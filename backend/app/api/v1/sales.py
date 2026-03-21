from fastapi import APIRouter, HTTPException
from typing import Optional
from app.core.deps import CurrentUser
from app.core.database import get_supabase_admin
from app.models.schemas import SaleCreate, SalesBulkCreate
from app.services.calculation import calculate_cost_per_portion
from app.services.audit import log_audit

router = APIRouter(prefix="/sales", tags=["Sotuvlar"])
db = get_supabase_admin()


@router.get("/")
async def list_sales(
    current_user: CurrentUser,
    daily_report_id: Optional[str] = None,
    product_id: Optional[str] = None
):
    q = db.table("sales").select(
        "*, products(name, unit, departments(name))"
    ).order("created_at", desc=True)

    if daily_report_id:
        q = q.eq("daily_report_id", daily_report_id)
    if product_id:
        q = q.eq("product_id", product_id)

    result = q.execute()
    return result.data


@router.post("/", status_code=201)
async def create_sale(body: SaleCreate, current_user: CurrentUser):
    """Bitta sotuv kiritish"""
    # Hisobotni tekshirish
    report = db.table("daily_reports").select("id, status, created_by").eq(
        "id", body.daily_report_id
    ).single().execute()

    if not report.data:
        raise HTTPException(404, "Hisobot topilmadi")
    if report.data["status"] == "approved":
        raise HTTPException(400, "Tasdiqlangan hisobotga sotuv qo'shib bo'lmaydi")
    if current_user["role"] == "manager" and report.data["created_by"] != current_user["id"]:
        raise HTTPException(403, "Ruxsat yo'q")

    # Tannarx hisoblash
    cost_per_unit = await calculate_cost_per_portion(body.product_id)

    data = body.model_dump()
    data["report_date"] = data.get("report_date")
    data["cost_per_unit"] = float(cost_per_unit)
    data["total_cost"] = float(cost_per_unit * body.quantity)
    data["created_by"] = current_user["id"]

    result = db.table("sales").insert(data).execute()
    await log_audit(current_user["id"], "sales", result.data[0]["id"], "INSERT", None, result.data[0])
    return result.data[0]


@router.post("/bulk", status_code=201)
async def create_sales_bulk(body: SalesBulkCreate, current_user: CurrentUser):
    """Ko'p sotuvni bir vaqtda kiritish (AI parse dan keyin)"""
    report = db.table("daily_reports").select("id, status, created_by").eq(
        "id", body.daily_report_id
    ).single().execute()

    if not report.data:
        raise HTTPException(404, "Hisobot topilmadi")
    if report.data["status"] == "approved":
        raise HTTPException(400, "Tasdiqlangan hisobotga sotuv qo'shib bo'lmaydi")

    items = []
    for item in body.items:
        cost = await calculate_cost_per_portion(item.product_id)
        items.append({
            "daily_report_id": body.daily_report_id,
            "product_id": item.product_id,
            "quantity": item.quantity,
            "unit_price": item.unit_price,
            "cost_per_unit": float(cost),
            "total_cost": float(cost * item.quantity),
            "input_method": item.input_method,
            "notes": item.notes,
            "created_by": current_user["id"],
        })

    result = db.table("sales").insert(items).execute()
    return {"inserted": len(result.data), "items": result.data}


@router.delete("/{sale_id}")
async def delete_sale(sale_id: str, current_user: CurrentUser):
    sale = db.table("sales").select("*, daily_reports(status, created_by)").eq(
        "id", sale_id
    ).single().execute()

    if not sale.data:
        raise HTTPException(404, "Sotuv topilmadi")

    report = sale.data.get("daily_reports", {})
    if report.get("status") == "approved":
        raise HTTPException(400, "Tasdiqlangan hisobotdan sotuv o'chirib bo'lmaydi")
    if current_user["role"] == "manager" and report.get("created_by") != current_user["id"]:
        raise HTTPException(403, "Ruxsat yo'q")

    db.table("sales").delete().eq("id", sale_id).execute()
    await log_audit(current_user["id"], "sales", sale_id, "DELETE", sale.data, None)
    return {"message": "Sotuv o'chirildi"}
