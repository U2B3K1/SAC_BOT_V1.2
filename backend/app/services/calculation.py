from decimal import Decimal
from typing import Optional
from datetime import date
from app.core.database import get_supabase_admin

db = get_supabase_admin()


async def calculate_cost_per_portion(product_id: str) -> Decimal:
    """
    1 porsiya mahsulotning tannarxini hisoblash.
    Retsept bo'yicha ingredientlar narxini yig'adi.
    """
    recipe = db.table("recipes").select(
        "id, recipe_ingredients(quantity, ingredients(cost_per_unit))"
    ).eq("product_id", product_id).single().execute()

    if not recipe.data:
        return Decimal("0")

    total_cost = Decimal("0")
    for ri in recipe.data.get("recipe_ingredients", []):
        qty = Decimal(str(ri["quantity"]))
        cost = Decimal(str(ri["ingredients"]["cost_per_unit"]))
        total_cost += qty * cost

    return total_cost


async def calculate_report_summary(report_id: str) -> dict:
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


async def calculate_theoretical_stock(as_of_date: date) -> list:
    """
    Har bir ingredient uchun teorik qoldiqni hisoblash:
    Boshlanish qoldig'i + kirimi - sotuvdan sarflash
    """
    ingredients = db.table("ingredients").select("id, name, unit").eq("is_active", True).execute()

    # Barcha stock'larni bir marta olish (N+1 o'rniga)
    all_stocks = db.table("inventory_stock").select("ingredient_id, quantity").execute()
    stock_map = {s["ingredient_id"]: s["quantity"] for s in all_stocks.data or []}

    # Barcha kirimlarni bir marta olish
    all_receipts = db.table("inventory_receipt_items").select(
        "ingredient_id, quantity, inventory_receipts!inner(receipt_date)"
    ).lte("inventory_receipts.receipt_date", as_of_date.isoformat()).execute()
    receipt_map = {}
    for r in all_receipts.data or []:
        receipt_map[r["ingredient_id"]] = receipt_map.get(r["ingredient_id"], 0) + r["quantity"]

    # Barcha retsept-ingredient bog'lanishlarini bir marta olish
    recipe_ings = db.table("recipe_ingredients").select(
        "ingredient_id, quantity, recipes!inner(product_id)"
    ).execute()
    # ingredient_id -> {product_id: qty_per_portion}
    ing_product_qty = {}
    for ri in recipe_ings.data or []:
        ing_id = ri["ingredient_id"]
        product_id = ri.get("recipes", {}).get("product_id")
        if product_id:
            if ing_id not in ing_product_qty:
                ing_product_qty[ing_id] = {}
            ing_product_qty[ing_id][product_id] = Decimal(str(ri["quantity"]))

    # Barcha sotuvlarni bir marta olish
    all_sales = db.table("sales").select(
        "quantity, product_id, daily_reports!inner(report_date)"
    ).lte("daily_reports.report_date", as_of_date.isoformat()).execute()

    result = []
    for ing in ingredients.data:
        ing_id = ing["id"]
        actual_qty = stock_map.get(ing_id, 0)
        total_received = receipt_map.get(ing_id, 0)

        # Bu ingredient uchun sarflashni hisoblash
        consumed = Decimal("0")
        product_qty_map = ing_product_qty.get(ing_id, {})
        for sale in all_sales.data or []:
            qty_per_portion = product_qty_map.get(sale["product_id"])
            if qty_per_portion:
                consumed += qty_per_portion * Decimal(str(sale["quantity"]))

        theoretical = actual_qty + total_received - float(consumed)

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


async def _calculate_consumed(ingredient_id: str, as_of_date: date) -> Decimal:
    """Sotuvdan sarflangan miqdorni hisoblash (retsept asosida)"""
    # Barcha retseptlarni bir marta olish (N+1 so'rov o'rniga)
    recipes = db.table("recipes").select(
        "id, product_id, recipe_ingredients(quantity)"
    ).execute()

    # product_id -> ingredient quantity mapping
    product_ingredient_qty = {}
    for recipe in recipes.data or []:
        for ri in recipe.get("recipe_ingredients", []):
            product_ingredient_qty[recipe["product_id"]] = Decimal(str(ri["quantity"]))

    # Ingredient uchun retsept ingredientlarini filtrlash
    recipe_ids = [r["id"] for r in recipes.data or []]
    if recipe_ids:
        recipe_ings = db.table("recipe_ingredients").select(
            "quantity, recipe_id, recipes!inner(product_id)"
        ).eq("ingredient_id", ingredient_id).execute()

        product_ingredient_qty = {}
        for ri in recipe_ings.data or []:
            product_id = ri.get("recipes", {}).get("product_id")
            if product_id:
                product_ingredient_qty[product_id] = Decimal(str(ri["quantity"]))

    # Sotuvlarni olish
    sales = db.table("sales").select(
        "quantity, product_id, daily_reports!inner(report_date)"
    ).lte("daily_reports.report_date", as_of_date.isoformat()).execute()

    total_consumed = Decimal("0")
    for sale in sales.data or []:
        qty_per_portion = product_ingredient_qty.get(sale["product_id"])
        if qty_per_portion:
            total_consumed += qty_per_portion * Decimal(str(sale["quantity"]))

    return total_consumed


def calculate_beverage_percentage(department_revenues: dict) -> float:
    """Ichimlik foizini hisoblash"""
    total = sum(department_revenues.values())
    if total == 0:
        return 0
    beverage = department_revenues.get("DRINK", 0)
    return (beverage / total) * 100
