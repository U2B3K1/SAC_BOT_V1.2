from fastapi import APIRouter, HTTPException
from typing import List, Optional
from datetime import date
from app.core.deps import CurrentUser
from app.core.database import get_supabase_admin
from app.models.schemas import DebtCreate, DebtPaymentCreate, SMSRequest
from app.services.sms import send_debt_reminder
from app.services.audit import log_audit

router = APIRouter(prefix="/debts", tags=["Qarzlar / CRM"])
db = get_supabase_admin()


@router.get("/")
async def list_debts(
    current_user: CurrentUser,
    status: Optional[str] = None,
    search: Optional[str] = None,
):
    q = db.table("debts").select(
        "*, debt_payments(amount, payment_date, notes)"
    ).order("created_at", desc=True)

    if status:
        q = q.eq("status", status)

    result = q.execute()
    data = result.data

    if search:
        search_lower = search.lower()
        data = [
            d for d in data
            if search_lower in (d.get("debtor_name") or "").lower()
            or search_lower in (d.get("phone") or "").lower()
            or search_lower in (d.get("organization") or "").lower()
        ]

    return data


@router.post("/", status_code=201)
async def create_debt(body: DebtCreate, current_user: CurrentUser):
    """Yangi qarz yozish"""
    data = body.model_dump()
    data["debt_date"] = data["debt_date"].isoformat()
    if data.get("due_date"):
        data["due_date"] = data["due_date"].isoformat()
    data["remaining_amount"] = body.initial_amount
    data["created_by"] = current_user["id"]

    result = db.table("debts").insert(data).execute()
    await log_audit(current_user["id"], "debts", result.data[0]["id"], "INSERT", None, result.data[0])
    return result.data[0]


@router.get("/{debt_id}")
async def get_debt(debt_id: str, current_user: CurrentUser):
    result = db.table("debts").select(
        "*, debt_payments(amount, payment_date, notes, created_at)"
    ).eq("id", debt_id).single().execute()
    if not result.data:
        raise HTTPException(404, "Qarz topilmadi")
    return result.data


@router.post("/{debt_id}/payments", status_code=201)
async def create_payment(debt_id: str, body: DebtPaymentCreate, current_user: CurrentUser):
    """Qarz to'lovi kiritish"""
    debt = db.table("debts").select("*").eq("id", debt_id).single().execute()
    if not debt.data:
        raise HTTPException(404, "Qarz topilmadi")
    if debt.data["status"] == "paid":
        raise HTTPException(400, "Bu qarz to'liq to'langan")
    if body.amount > debt.data["remaining_amount"]:
        raise HTTPException(400, f"To'lov summasi qoldiqdan ({debt.data['remaining_amount']:.2f}) katta bo'lishi mumkin emas")

    data = body.model_dump()
    data["payment_date"] = data["payment_date"].isoformat()
    data["debt_id"] = debt_id
    data["created_by"] = current_user["id"]

    result = db.table("debt_payments").insert(data).execute()
    # Trigger avtomatik remaining_amount va status yangilaydi
    await log_audit(current_user["id"], "debt_payments", result.data[0]["id"], "INSERT", None, result.data[0])
    return result.data[0]


@router.post("/{debt_id}/sms")
async def send_sms_reminder(debt_id: str, body: SMSRequest, current_user: CurrentUser):
    """SMS eslatma yuborish"""
    debt = db.table("debts").select("*").eq("id", debt_id).single().execute()
    if not debt.data:
        raise HTTPException(404, "Qarz topilmadi")
    if not debt.data.get("phone"):
        raise HTTPException(400, "Telefon raqami yo'q")

    message = body.custom_message or (
        f"Hurmatli {debt.data['debtor_name']}, "
        f"sizning {debt.data['remaining_amount']:,.0f} so'm qarz qoldig'ingiz bor. "
        f"Iltimos, to'lovni amalga oshiring."
    )

    result = await send_debt_reminder(debt.data["phone"], message)

    # SMS hisoblagichni yangilash
    db.table("debts").update({
        "sms_sent_count": (debt.data.get("sms_sent_count") or 0) + 1
    }).eq("id", debt_id).execute()

    return {"message": "SMS yuborildi", "phone": debt.data["phone"], "result": result}


@router.patch("/{debt_id}")
async def update_debt(debt_id: str, current_user: CurrentUser, notes: Optional[str] = None):
    """Qarz eslatmasini yangilash"""
    if notes:
        result = db.table("debts").update({"notes": notes}).eq("id", debt_id).execute()
        return result.data[0]
    raise HTTPException(400, "Yangilanadigan ma'lumot yo'q")
