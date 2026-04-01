from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from typing import Optional
import uuid
import os
from app.core.deps import CurrentUser
from app.core.database import get_supabase_admin
from app.core.config import settings
from app.models.schemas import AIConfirmRequest
from app.services.ai_parser import parse_screenshot, parse_audio, parse_excel_file

router = APIRouter(prefix="/ai", tags=["AI Parsing"])
db = get_supabase_admin()


async def _save_file_to_storage(file: UploadFile, folder: str) -> str:
    from fastapi.concurrency import run_in_threadpool
    """Faylni Supabase Storage'ga yuklash"""
    ext = os.path.splitext(file.filename)[1] if file.filename else ""
    filename = f"{folder}/{uuid.uuid4()}{ext}"
    content = await file.read()

    def sync_upload():
        try:
            db.storage.from_("uploads").upload(
                path=filename,
                file=content,
                file_options={"content-type": file.content_type or "application/octet-stream"}
            )
        except Exception as e:
            if "not found" in str(e).lower():
                # Agar bucket yo'q bo'lsa, yaratamiz va qayta yuklaymiz
                try:
                    db.storage.create_bucket("uploads", name="uploads", options={"public": True})
                    db.storage.from_("uploads").upload(
                        path=filename,
                        file=content,
                        file_options={"content-type": file.content_type or "application/octet-stream"}
                    )
                except Exception:
                    raise e
            else:
                raise e

    await run_in_threadpool(sync_upload)

    file_url = f"{settings.SUPABASE_URL}/storage/v1/object/public/uploads/{filename}"
    return file_url


@router.post("/parse-screenshot")
async def parse_screenshot_endpoint(
    background_tasks: BackgroundTasks,
    current_user: CurrentUser,
    file: UploadFile = File(...),
):
    """Screenshot yuklab AI bilan tahlil qilish"""
    if not file.content_type.startswith("image/"):
        raise HTTPException(400, "Faqat rasm fayli qabul qilinadi")

    file_url = await _save_file_to_storage(file, "screenshots")

    # Session yaratish
    session = db.table("ai_parse_sessions").insert({
        "session_type": "screenshot",
        "file_url": file_url,
        "status": "pending",
        "created_by": current_user["id"],
    }).execute()
    session_id = session.data[0]["id"]

    # Background'da parse qilish
    background_tasks.add_task(parse_screenshot, session_id, file_url)

    return {
        "session_id": session_id,
        "status": "pending",
        "message": "Rasm yuborildi, tahlil boshlanmoqda..."
    }


@router.post("/parse-audio")
async def parse_audio_endpoint(
    background_tasks: BackgroundTasks,
    current_user: CurrentUser,
    file: UploadFile = File(...),
):
    """Audio yuklab Whisper bilan transkripsiya qilish"""
    allowed = ["audio/ogg", "audio/mpeg", "audio/wav", "audio/mp4", "audio/webm"]
    if file.content_type not in allowed:
        raise HTTPException(400, "Noto'g'ri audio format. Qo'llab-quvvatlanadi: ogg, mp3, wav")

    file_url = await _save_file_to_storage(file, "audio")

    session = db.table("ai_parse_sessions").insert({
        "session_type": "audio",
        "file_url": file_url,
        "status": "pending",
        "created_by": current_user["id"],
    }).execute()
    session_id = session.data[0]["id"]

    background_tasks.add_task(parse_audio, session_id, file_url)

    return {
        "session_id": session_id,
        "status": "pending",
        "message": "Audio yuborildi, transkripsiya boshlanmoqda..."
    }


@router.post("/import-excel")
async def import_excel_endpoint(
    background_tasks: BackgroundTasks,
    current_user: CurrentUser,
    file: UploadFile = File(...),
):
    """Excel fayl import qilish"""
    allowed = [
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
    ]
    if file.content_type not in allowed and not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(400, "Faqat Excel fayl (.xlsx, .xls) qabul qilinadi")

    content = await file.read()
    file_url = await _save_file_to_storage(file, "excel")

    session = db.table("ai_parse_sessions").insert({
        "session_type": "excel",
        "file_url": file_url,
        "status": "pending",
        "created_by": current_user["id"],
    }).execute()
    session_id = session.data[0]["id"]

    background_tasks.add_task(parse_excel_file, session_id, content)

    return {
        "session_id": session_id,
        "status": "pending",
        "message": "Excel fayl tahlil qilinmoqda..."
    }


@router.get("/sessions/{session_id}")
def get_session(session_id: str, current_user: CurrentUser):
    """AI parsing natijasini olish"""
    result = db.table("ai_parse_sessions").select("*").eq("id", session_id).single().execute()
    if not result.data:
        raise HTTPException(404, "Session topilmadi")
    return result.data


@router.post("/sessions/{session_id}/confirm")
def confirm_session(session_id: str, body: AIConfirmRequest, current_user: CurrentUser):
    """
    AI natijasini tasdiqlash — ma'lumotlarni DB ga yozish.
    confirmed_data ichida sotuvlar yoki xarajatlar bo'lishi kerak.
    """
    from datetime import datetime

    session = db.table("ai_parse_sessions").select("*").eq("id", session_id).single().execute()
    if not session.data:
        raise HTTPException(404, "Session topilmadi")
    if session.data["status"] == "confirmed":
        raise HTTPException(400, "Bu session allaqachon tasdiqlangan")

    confirmed_data = body.confirmed_data
    daily_report_id = body.daily_report_id

    # Agar sotuv ma'lumotlari bo'lsa
    if "sales" in confirmed_data and daily_report_id:
        from app.services.calculation import calculate_cost_per_portion
        items = []
        for s in confirmed_data["sales"]:
            cost = calculate_cost_per_portion(s["product_id"])
            items.append({
                "daily_report_id": daily_report_id,
                "product_id": s["product_id"],
                "quantity": s["quantity"],
                "unit_price": s["unit_price"],
                "cost_per_unit": float(cost),
                "total_cost": float(cost * s["quantity"]),
                "input_method": session.data["session_type"],
                "ai_session_id": session_id,
                "created_by": current_user["id"],
            })
        if items:
            db.table("sales").insert(items).execute()

    # Agar xarajat bo'lsa
    if "expenses" in confirmed_data and daily_report_id:
        items = []
        for e in confirmed_data["expenses"]:
            items.append({
                "daily_report_id": daily_report_id,
                "category_id": e["category_id"],
                "amount": e["amount"],
                "description": e.get("description"),
                "input_method": session.data["session_type"],
                "ai_session_id": session_id,
                "created_by": current_user["id"],
            })
        if items:
            db.table("expenses").insert(items).execute()

    # Session ni tasdiqlash
    db.table("ai_parse_sessions").update({
        "status": "confirmed",
        "parsed_data": confirmed_data,
        "confirmed_by": current_user["id"],
        "confirmed_at": datetime.utcnow().isoformat(),
    }).eq("id", session_id).execute()

    return {"message": "Ma'lumotlar saqlandi", "session_id": session_id}


@router.post("/sessions/{session_id}/reject")
def reject_session(session_id: str, current_user: CurrentUser):
    """AI natijasini rad etish"""
    db.table("ai_parse_sessions").update({
        "status": "rejected",
        "confirmed_by": current_user["id"],
    }).eq("id", session_id).execute()
    return {"message": "Session rad etildi"}
