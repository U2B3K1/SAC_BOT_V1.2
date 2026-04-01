from decimal import Decimal
from typing import Optional
from datetime import date
import time
from app.core.database import get_supabase_admin

db = get_supabase_admin()

# =============================================
# Recipe cost cache (TTL: 5 daqiqa)
# Bulk sales da bir xil mahsulot uchun
# qayta-qayta DB query yuborishni oldini oladi
# =============================================
_recipe_cost_cache: dict[str, tuple[Decimal, float]] = {}
_RECIPE_CACHE_TTL = 300  # 5 daqiqa


def _get_cached_cost(product_id: str) -> Decimal | None:
    if product_id in _recipe_cost_cache:
        cost, cached_at = _recipe_cost_cache[product_id]
        if time.time() - cached_at < _RECIPE_CACHE_TTL:
            return cost
        del _recipe_cost_cache[product_id]
    return None


def invalidate_recipe_cache(product_id: str | None = None):
    """Retsept o'zgarganda cache tozalash"""
    if product_id:
        _recipe_cost_cache.pop(product_id, None)
    else:
        _recipe_cost_cache.clear()


def calculate_cost_per_portion(product_id: str) -> Decimal:
    """
    1 porsiya mahsulotning tannarxini hisoblash.
    Cache bilan — bulk operatsiyalarda tezkor.
    """
    # Cache dan tekshirish
    cached = _get_cached_cost(product_id)
    if cached is not None:
        return cached

    recipe = db.table("recipes").select(
        "id, recipe_ingredients(quantity, ingredients(cost_per_unit))"
    ).eq("product_id", product_id).single().execute()

    if not recipe.data:
        _recipe_cost_cache[product_id] = (Decimal("0"), time.time())
        return Decimal("0")

    total_cost = Decimal("0")
    for ri in recipe.data.get("recipe_ingredients", []):
        qty = Decimal(str(ri["quantity"]))
        cost = Decimal(str(ri["ingredients"]["cost_per_unit"]))
        total_cost += qty * cost

    # Cache ga saqlash
    _recipe_cost_cache[product_id] = (total_cost, time.time())
    return total_cost


def calculate_report_summary(report_id: str) -> dict:
    """Hisobot yig'masini hisoblash"""
    report = db.table("daily_reports").select("*").eq("id", report_id).single().execute()
    if not report.data:
        return {}

    sales = db.table("sales").select("total_amount,total_cost").eq("daily_report_id", report_id).execute()
    expenses = db.table("expenses").select("amount").eq("daily_report_id", report_id).execute()

    total_revenue = sum(Decimal(str(s.get("total_amount", 0) or 0)) for s in sales.data)
    total_cost = sum(Decimal(str(s.get("total_cost", 0) or 0)) for s in sales.data)
    total_expenses = sum(Decimal(str(e.get("amount", 0) or 0)) for e in expenses.data)

    gross_profit = total_revenue - total_cost
    net_profit = gross_profit - total_expenses
    opening = Decimal(str(report.data.get("opening_balance", 0) or 0))
    closing = opening + total_revenue - total_expenses - total_cost

    return {
        "total_revenue": float(total_revenue),
        "total_cost": float(total_cost),
        "gross_profit": float(gross_profit),
        "total_expenses": float(total_expenses),
        "net_profit": float(net_profit),
        "opening_balance": float(opening),
        "closing_balance": float(closing),
        "margin_pct": float((gross_profit / total_revenue * 100) if total_revenue > 0 else 0),
    }


def calculate_theoretical_stock(as_of_date: date) -> list:
    """
    Har bir ingredient uchun teorik qoldiqni hisoblash:
    Boshlanish qoldig'i + kirimi - sotuvdan sarflash
    Barcha ma'lumotlar bitta/ikkita so'rovda RAMga yuklanib, shu yerda hisoblanadi (O(1) HTTP queries).
    """
    date_str = as_of_date.isoformat()

    # 1. Barcha aktiv ingredientlar
    ingredients_resp = db.table("ingredients").select("id, name, unit").eq("is_active", True).execute()
    ingredients = ingredients_resp.data

    # 2. Joriy real qoldiq
    stock_resp = db.table("inventory_stock").select("ingredient_id, quantity").execute()
    stock_map = {item["ingredient_id"]: item["quantity"] for item in stock_resp.data}

    # 3. Kirim qilingan barcha tovarlar (as_of_date gacha)
    # Eslatma: Supabase 'inner' join lte bilan birga yaxshi ishlashi mumkin. Qiyinchilik tug'dirmasligi uchun hamma receiptni olamiz.
    receipts_resp = db.table("inventory_receipt_items").select(
        "ingredient_id, quantity, inventory_receipts!inner(receipt_date)"
    ).lte("inventory_receipts.receipt_date", date_str).execute()
    
    received_map = {}
    for r in receipts_resp.data:
        iid = r["ingredient_id"]
        qty = r.get("quantity", 0) or 0
        received_map[iid] = received_map.get(iid, Decimal("0")) + Decimal(str(qty))

    # 4. Sotuvlarni olish (as_of_date gacha)
    sales_resp = db.table("sales").select(
        "product_id, quantity, daily_reports!inner(report_date)"
    ).lte("daily_reports.report_date", date_str).execute()

    sales_map = {} # product_id -> sum of sales quantity
    for s in sales_resp.data:
        pid = s["product_id"]
        sqty = s.get("quantity", 0) or 0
        sales_map[pid] = sales_map.get(pid, Decimal("0")) + Decimal(str(sqty))

    # 5. Barcha retseptlar va ularning ingredientlarini olish
    recipes_resp = db.table("recipes").select("product_id, recipe_ingredients(ingredient_id, quantity)").execute()
    # retsept bo'yicha ingredient sarfini xaritasi: ingredient_id -> sarflangan_miqdor
    consumed_map = {}
    for recipe in recipes_resp.data:
        pid = recipe["product_id"]
        if pid not in sales_map:
            continue
        
        sold_qty = sales_map[pid] # bu maxsulotdan jami qancha porsiya sotilgan
        for ri in recipe.get("recipe_ingredients", []):
            iid = ri["ingredient_id"]
            ri_qty = Decimal(str(ri.get("quantity", 0) or 0))
            consumed_map[iid] = consumed_map.get(iid, Decimal("0")) + (sold_qty * ri_qty)

    # Natijani shakllantiramiz
    result = []
    for ing in ingredients:
        ing_id = ing["id"]
        
        actual_qty = Decimal(str(stock_map.get(ing_id, 0)))
        total_received = received_map.get(ing_id, Decimal("0"))
        consumed = consumed_map.get(ing_id, Decimal("0"))
        
        theoretical = actual_qty + total_received - consumed

        result.append({
            "ingredient_id": ing_id,
            "ingredient_name": ing["name"],
            "unit": ing["unit"],
            "actual_qty": float(actual_qty),
            "total_received": float(total_received),
            "consumed": float(consumed),
            "theoretical_qty": float(theoretical),
            "variance": float(actual_qty - theoretical),
        })

    return result


def calculate_beverage_percentage(department_revenues: dict) -> float:
    """Ichimlik foizini hisoblash"""
    total = sum(department_revenues.values())
    if total == 0:
        return 0
    beverage = department_revenues.get("DRINK", 0)
    return (beverage / total) * 100
