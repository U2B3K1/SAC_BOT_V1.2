from fastapi import APIRouter, HTTPException, Query
from datetime import date, timedelta
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
from app.core.deps import CurrentUser, SuperUser
from app.core.database import get_supabase_admin
from app.models.schemas import DailyReportCreate, DailyReportUpdate
from app.services.audit import log_audit

router = APIRouter(prefix="/reports", tags=["Hisobotlar"])
db = get_supabase_admin()


@router.get("/daily")
def list_daily_reports(
    current_user: CurrentUser,
    report_date: Optional[date] = None,
    department_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """Kunlik hisobotlar ro'yxati"""
    q = db.table("daily_reports").select(
        "*, departments(name, code), users(full_name)"
    ).order("report_date", desc=True).limit(limit).offset(offset)

    # Manager faqat o'z hisobotlarini ko'radi
    if current_user["role"] == "manager":
        q = q.eq("created_by", current_user["id"])

    if report_date:
        q = q.eq("report_date", report_date.isoformat())
    if department_id:
        q = q.eq("department_id", department_id)

    result = q.execute()
    return result.data


@router.post("/daily", status_code=201)
def create_daily_report(body: DailyReportCreate, current_user: CurrentUser):
    """Yangi kunlik hisobot yaratish"""
    # Bir xil kun va bo'lim uchun mavjudligini tekshirish
    existing = db.table("daily_reports").select("id").eq(
        "report_date", body.report_date.isoformat()
    ).eq("department_id", body.department_id).execute()

    if existing.data:
        raise HTTPException(400, "Bu sana va bo'lim uchun hisobot allaqachon mavjud")

    data = body.model_dump()
    data["report_date"] = data["report_date"].isoformat()
    data["created_by"] = current_user["id"]
    result = db.table("daily_reports").insert(data).execute()
    log_audit(current_user["id"], "daily_reports", result.data[0]["id"], "INSERT", None, result.data[0])
    return result.data[0]


@router.get("/daily/{report_id}")
def get_daily_report(report_id: str, current_user: CurrentUser):
    """Hisobot detali: sotuv + xarajat bilan — parallel queries"""
    # 1-QUERY: Avval hisobotni tekshirish (access control uchun)
    report = db.table("daily_reports").select(
        "*, departments(name,code), users(full_name)"
    ).eq("id", report_id).single().execute()

    if not report.data:
        raise HTTPException(404, "Hisobot topilmadi")

    # Manager faqat o'zini ko'radi
    if current_user["role"] == "manager" and report.data["created_by"] != current_user["id"]:
        raise HTTPException(403, "Ruxsat yo'q")

    # 2 & 3 — Sotuvlar + Xarajatlarni PARALLEL yuklash (2x tezroq)
    def fetch_sales():
        return db.table("sales").select(
            "*, products(name, unit)"
        ).eq("daily_report_id", report_id).execute().data

    def fetch_expenses():
        return db.table("expenses").select(
            "*, expense_categories(name, code)"
        ).eq("daily_report_id", report_id).execute().data

    with ThreadPoolExecutor(max_workers=2) as executor:
        sales_future = executor.submit(fetch_sales)
        expenses_future = executor.submit(fetch_expenses)
        sales_data = sales_future.result()
        expenses_data = expenses_future.result()

    return {
        **report.data,
        "sales": sales_data,
        "expenses": expenses_data,
    }


@router.patch("/daily/{report_id}")
def update_daily_report(report_id: str, body: DailyReportUpdate, current_user: CurrentUser):
    """Hisobotni yangilash (faqat draft holat)"""
    report = db.table("daily_reports").select("*").eq("id", report_id).single().execute()
    if not report.data:
        raise HTTPException(404, "Hisobot topilmadi")

    if report.data["status"] != "draft":
        raise HTTPException(400, "Tasdiqlangan hisobotni o'zgartirish mumkin emas")

    if current_user["role"] == "manager" and report.data["created_by"] != current_user["id"]:
        raise HTTPException(403, "Ruxsat yo'q")

    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    result = db.table("daily_reports").update(updates).eq("id", report_id).execute()
    return result.data[0]


@router.post("/daily/{report_id}/submit")
def submit_report(report_id: str, current_user: CurrentUser):
    """Hisobotni tasdiqlash uchun yuborish"""
    from datetime import datetime
    report = db.table("daily_reports").select("*").eq("id", report_id).single().execute()
    if not report.data:
        raise HTTPException(404, "Hisobot topilmadi")
    if report.data["status"] != "draft":
        raise HTTPException(400, "Hisobot allaqachon tasdiqgan")

    result = db.table("daily_reports").update({
        "status": "submitted",
        "submitted_at": datetime.utcnow().isoformat()
    }).eq("id", report_id).execute()
    log_audit(current_user["id"], "daily_reports", report_id, "UPDATE", report.data, result.data[0])
    return {"message": "Hisobot yuborildi", "status": "submitted"}


@router.post("/daily/{report_id}/approve")
def approve_report(report_id: str, current_user: SuperUser):
    """Hisobotni tasdiqlash (faqat Super User)"""
    result = db.table("daily_reports").update({"status": "approved"}).eq("id", report_id).execute()
    return {"message": "Hisobot tasdiqlandi", "status": "approved"}


@router.get("/range")
def reports_range(
    current_user: CurrentUser,
    date_from: date = Query(...),
    date_to: date = Query(...),
    department_id: Optional[str] = None
):
    """Sana oralig'i bo'yicha yig'ma hisobot"""
    q = db.table("daily_reports").select(
        "*, departments(name,code)"
    ).gte("report_date", date_from.isoformat()).lte("report_date", date_to.isoformat())

    if current_user["role"] == "manager":
        q = q.eq("created_by", current_user["id"])
    if department_id:
        q = q.eq("department_id", department_id)

    result = q.order("report_date").execute()
    reports = result.data

    # Yig'ma hisoblash
    summary = {
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "total_revenue": sum(r.get("total_revenue", 0) or 0 for r in reports),
        "total_cost": sum(r.get("total_cost", 0) or 0 for r in reports),
        "gross_profit": sum(r.get("gross_profit", 0) or 0 for r in reports),
        "total_expenses": sum(r.get("total_expenses", 0) or 0 for r in reports),
        "net_profit": sum(r.get("net_profit", 0) or 0 for r in reports),
        "report_count": len(reports),
        "reports": reports,
    }
    return summary


@router.get("/summary/{days}")
def reports_summary(days: int, current_user: CurrentUser, department_id: Optional[str] = None):
    """3 yoki 5 kunlik yig'ma hisobot"""
    if days not in [3, 5, 7, 10, 30]:
        raise HTTPException(400, "Faqat 3, 5, 7, 10, 30 kunlik hisobot qo'llab-quvvatlanadi")

    date_to = date.today()
    date_from = date_to - timedelta(days=days - 1)

    q = db.table("daily_reports").select("*, departments(name, code)").gte(
        "report_date", date_from.isoformat()
    ).lte("report_date", date_to.isoformat())

    if current_user["role"] == "manager":
        q = q.eq("created_by", current_user["id"])
    if department_id:
        q = q.eq("department_id", department_id)

    result = q.order("report_date").execute()
    reports = result.data

    return {
        "period_days": days,
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "total_revenue": sum(r.get("total_revenue", 0) or 0 for r in reports),
        "total_cost": sum(r.get("total_cost", 0) or 0 for r in reports),
        "gross_profit": sum(r.get("gross_profit", 0) or 0 for r in reports),
        "total_expenses": sum(r.get("total_expenses", 0) or 0 for r in reports),
        "net_profit": sum(r.get("net_profit", 0) or 0 for r in reports),
        "reports": reports,
    }
