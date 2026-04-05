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
def list_sales(
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
def create_sale(body: SaleCreate, current_user: CurrentUser):
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

    # FIFO va Ledger bilan atomik sotuv kiritish
    result = db.rpc("process_sale_fifo", {
        "p_daily_report_id": body.daily_report_id,
        "p_product_id": body.product_id,
        "p_quantity": body.quantity,
        "p_unit_price": body.unit_price,
        "p_created_by": current_user["id"]
    }).execute()

    sale_id = result.data
    new_sale = db.table("sales").select("*").eq("id", sale_id).single().execute()
    
    log_audit(current_user["id"], "sales", sale_id, "INSERT", None, new_sale.data)
    return new_sale.data


@router.post("/bulk", status_code=201)
def create_sales_bulk(body: SalesBulkCreate, current_user: CurrentUser):
    """Ko'p sotuvni bir vaqtda kiritish (AI parse dan keyin)"""
    report = db.table("daily_reports").select("id, status, created_by").eq(
        "id", body.daily_report_id
    ).single().execute()

    if not report.data:
        raise HTTPException(404, "Hisobot topilmadi")
    if report.data["status"] == "approved":
        raise HTTPException(400, "Tasdiqlangan hisobotga sotuv qo'shib bo'lmaydi")

    inserted_ids = []
    for item in body.items:
        # FIFO va Ledger bilan atomik sotuv kiritish
        res = db.rpc("process_sale_fifo", {
            "p_daily_report_id": body.daily_report_id,
            "p_product_id": item.product_id,
            "p_quantity": item.quantity,
            "p_unit_price": item.unit_price,
            "p_created_by": current_user["id"]
        }).execute()
        inserted_ids.append(res.data)

    return {"inserted_count": len(inserted_ids), "ids": inserted_ids}


@router.delete("/{sale_id}")
def delete_sale(sale_id: str, current_user: CurrentUser):
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
    log_audit(current_user["id"], "sales", sale_id, "DELETE", sale.data, None)
    return {"message": "Sotuv o'chirildi"}
