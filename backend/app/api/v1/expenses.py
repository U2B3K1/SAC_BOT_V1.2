from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import Optional
from app.core.deps import CurrentUser
from app.core.database import get_supabase_admin
from app.models.schemas import ExpenseCreate

router = APIRouter(prefix="/expenses", tags=["Xarajatlar"])
db = get_supabase_admin()


@router.get("/")
async def list_expenses(
    current_user: CurrentUser,
    daily_report_id: Optional[str] = None
):
    q = db.table("expenses").select(
        "*, expense_categories(name, code), users(full_name)"
    ).order("created_at", desc=True)

    if daily_report_id:
        q = q.eq("daily_report_id", daily_report_id)
    if current_user["role"] == "manager":
        q = q.eq("created_by", current_user["id"])

    return q.execute().data


@router.post("/", status_code=201)
async def create_expense(body: ExpenseCreate, current_user: CurrentUser):
    """Xarajat kiritish"""
    report = db.table("daily_reports").select("id,status,created_by").eq(
        "id", body.daily_report_id
    ).single().execute()
    if not report.data:
        raise HTTPException(404, "Hisobot topilmadi")
    if report.data["status"] == "approved":
        raise HTTPException(400, "Tasdiqlangan hisobotga xarajat qo'shib bo'lmaydi")
    if current_user["role"] == "manager" and report.data["created_by"] != current_user["id"]:
        raise HTTPException(403, "Ruxsat yo'q")

    data = body.model_dump()
    data["created_by"] = current_user["id"]
    result = db.table("expenses").insert(data).execute()
    return result.data[0]


@router.delete("/{expense_id}")
async def delete_expense(expense_id: str, current_user: CurrentUser):
    expense = db.table("expenses").select(
        "*, daily_reports(status, created_by)"
    ).eq("id", expense_id).single().execute()

    if not expense.data:
        raise HTTPException(404, "Xarajat topilmadi")

    report = expense.data.get("daily_reports", {})
    if report.get("status") == "approved":
        raise HTTPException(400, "Tasdiqlangan hisobotdan xarajat o'chirib bo'lmaydi")

    db.table("expenses").delete().eq("id", expense_id).execute()
    return {"message": "Xarajat o'chirildi"}
