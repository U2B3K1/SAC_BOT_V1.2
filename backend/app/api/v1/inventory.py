from fastapi import APIRouter, HTTPException
from typing import List, Optional
from datetime import date
from app.core.deps import CurrentUser
from app.core.database import get_supabase_admin
from app.models.schemas import InventoryReceiptCreate, StockUpdateItem

router = APIRouter(prefix="/inventory", tags=["Ombor"])
db = get_supabase_admin()


@router.get("/stock")
def get_current_stock(current_user: CurrentUser):
    """Barcha ingredientlarning joriy qoldig'i"""
    result = db.table("inventory_stock").select(
        "*, ingredients(name, unit, cost_per_unit)"
    ).execute()
    return result.data


@router.get("/stock/{ingredient_id}")
def get_ingredient_stock(ingredient_id: str, current_user: CurrentUser):
    result = db.table("inventory_stock").select(
        "*, ingredients(name, unit)"
    ).eq("ingredient_id", ingredient_id).single().execute()
    if not result.data:
        return {"ingredient_id": ingredient_id, "quantity": 0}
    return result.data


@router.patch("/stock")
def update_stock_actual(body: List[StockUpdateItem], current_user: CurrentUser):
    """Faktik qoldiqni kiritish (inventarizatsiya) - batch optimized"""
    from datetime import datetime

    if not body:
        return {"updated": 0, "adjustments": []}

    ingredient_ids = [item.ingredient_id for item in body]
    now_str = datetime.utcnow().isoformat()
    today_str = date.today().isoformat()

    # 1-QUERY: Barcha ingredientlarning joriy stock'ini bir vaqtda olish
    stocks_result = db.table("inventory_stock").select(
        "ingredient_id, quantity"
    ).in_("ingredient_id", ingredient_ids).execute()

    # Stock'ni dict'ga o'girish (tez qidirish uchun)
    stock_map = {s["ingredient_id"]: s["quantity"] for s in stocks_result.data}

    # 2-QUERY: Barcha adjustmentlarni batch insert
    adjustments_data = [
        {
            "ingredient_id": item.ingredient_id,
            "adj_date": today_str,
            "theoretical_qty": float(stock_map.get(item.ingredient_id, 0)),
            "actual_qty": item.actual_qty,
            "reason": item.reason,
            "created_by": current_user["id"],
        }
        for item in body
    ]
    adj_result = db.table("inventory_adjustments").insert(adjustments_data).execute()

    # 3-QUERY: Barcha stock'larni batch upsert
    stock_updates = [
        {
            "ingredient_id": item.ingredient_id,
            "quantity": item.actual_qty,
            "last_counted_at": now_str,
            "last_updated_at": now_str,
        }
        for item in body
    ]
    db.table("inventory_stock").upsert(
        stock_updates, on_conflict="ingredient_id"
    ).execute()

    return {"updated": len(adj_result.data), "adjustments": adj_result.data}


@router.post("/receipts", status_code=201)
def create_receipt(body: InventoryReceiptCreate, current_user: CurrentUser):
    """Yangi ombor kirimi"""
    items_data = [item.model_dump() for item in body.items]
    
    result = db.rpc("process_inventory_receipt", {
        "p_receipt_date": body.receipt_date.isoformat(),
        "p_department_id": body.department_id,
        "p_supplier": body.supplier,
        "p_items": items_data,
        "p_is_paid": body.is_paid,
        "p_created_by": current_user["id"]
    }).execute()

    receipt_id = result.data

    return db.table("inventory_receipts").select(
        "*, inventory_receipt_items(*, ingredients(name, unit))"
    ).eq("id", receipt_id).single().execute().data


@router.get("/receipts")
def list_receipts(
    current_user: CurrentUser,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    limit: int = 50
):
    q = db.table("inventory_receipts").select(
        "*, inventory_receipt_items(quantity, unit_cost, ingredients(name, unit))"
    ).order("receipt_date", desc=True).limit(limit)

    if date_from:
        q = q.gte("receipt_date", date_from.isoformat())
    if date_to:
        q = q.lte("receipt_date", date_to.isoformat())

    return q.execute().data


@router.get("/variance")
def get_stock_variance(current_user: CurrentUser):
    """Real vs teorik qoldiq farqi"""
    adjustments = db.table("inventory_adjustments").select(
        "*, ingredients(name, unit)"
    ).order("adj_date", desc=True).limit(100).execute()

    return {
        "adjustments": adjustments.data,
        "summary": {
            "total_records": len(adjustments.data),
            "discrepancies": [a for a in adjustments.data if abs(a.get("difference", 0) or 0) > 0.01]
        }
    }


@router.get("/theoretical")
def get_theoretical_stock(current_user: CurrentUser, as_of_date: Optional[date] = None):
    """Sotuv va kirimi asosida hisoblangan teorik qoldiq"""
    from app.services.calculation import calculate_theoretical_stock
    result = calculate_theoretical_stock(as_of_date or date.today())
    return result
