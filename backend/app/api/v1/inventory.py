from fastapi import APIRouter, HTTPException
from typing import List, Optional
from datetime import date
from app.core.deps import CurrentUser
from app.core.database import get_supabase_admin
from app.models.schemas import InventoryReceiptCreate, StockUpdateItem

router = APIRouter(prefix="/inventory", tags=["Ombor"])
db = get_supabase_admin()


@router.get("/stock")
async def get_current_stock(current_user: CurrentUser):
    """Barcha ingredientlarning joriy qoldig'i"""
    result = db.table("inventory_stock").select(
        "*, ingredients(name, unit, cost_per_unit)"
    ).execute()
    return result.data


@router.get("/stock/{ingredient_id}")
async def get_ingredient_stock(ingredient_id: str, current_user: CurrentUser):
    result = db.table("inventory_stock").select(
        "*, ingredients(name, unit)"
    ).eq("ingredient_id", ingredient_id).single().execute()
    if not result.data:
        return {"ingredient_id": ingredient_id, "quantity": 0}
    return result.data


@router.patch("/stock")
async def update_stock_actual(body: List[StockUpdateItem], current_user: CurrentUser):
    """Faktik qoldiqni kiritish (inventarizatsiya)"""
    from datetime import datetime
    results = []
    for item in body:
        # Teorik qoldiqni olish
        stock = db.table("inventory_stock").select("quantity").eq(
            "ingredient_id", item.ingredient_id
        ).execute()
        theoretical = stock.data[0]["quantity"] if stock.data else 0

        # inventory_adjustments ga yozish
        adj = db.table("inventory_adjustments").insert({
            "ingredient_id": item.ingredient_id,
            "adj_date": date.today().isoformat(),
            "theoretical_qty": float(theoretical),
            "actual_qty": item.actual_qty,
            "reason": item.reason,
            "created_by": current_user["id"],
        }).execute()

        # Faktik qoldiqni stock'da yangilash
        db.table("inventory_stock").upsert({
            "ingredient_id": item.ingredient_id,
            "quantity": item.actual_qty,
            "last_counted_at": datetime.utcnow().isoformat(),
            "last_updated_at": datetime.utcnow().isoformat(),
        }, on_conflict="ingredient_id").execute()

        results.append(adj.data[0])
    return {"updated": len(results), "adjustments": results}


@router.post("/receipts", status_code=201)
async def create_receipt(body: InventoryReceiptCreate, current_user: CurrentUser):
    """Yangi ombor kirimi"""
    receipt_data = {
        "receipt_date": body.receipt_date.isoformat(),
        "department_id": body.department_id,
        "supplier": body.supplier,
        "notes": body.notes,
        "created_by": current_user["id"],
    }
    # Jami summani hisoblash
    total = sum(item.quantity * item.unit_cost for item in body.items)
    receipt_data["total_amount"] = float(total)

    receipt_result = db.table("inventory_receipts").insert(receipt_data).execute()
    receipt_id = receipt_result.data[0]["id"]

    # Itemlarni kiritish (trigger avtomatik stock yangilaydi)
    items = [
        {
            "receipt_id": receipt_id,
            "ingredient_id": item.ingredient_id,
            "quantity": item.quantity,
            "unit": item.unit,
            "unit_cost": item.unit_cost,
        }
        for item in body.items
    ]
    db.table("inventory_receipt_items").insert(items).execute()

    return db.table("inventory_receipts").select(
        "*, inventory_receipt_items(*, ingredients(name, unit))"
    ).eq("id", receipt_id).single().execute().data


@router.get("/receipts")
async def list_receipts(
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
async def get_stock_variance(current_user: CurrentUser):
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
async def get_theoretical_stock(current_user: CurrentUser, as_of_date: Optional[date] = None):
    """Sotuv va kirimi asosida hisoblangan teorik qoldiq"""
    from app.services.calculation import calculate_theoretical_stock
    result = await calculate_theoretical_stock(as_of_date or date.today())
    return result
