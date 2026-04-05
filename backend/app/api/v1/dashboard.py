from fastapi import APIRouter, Query
from datetime import date
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
from app.core.deps import CurrentUser
from app.core.database import get_supabase_admin

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])
db = get_supabase_admin()


@router.get("/stats")
def dashboard_stats(
    current_user: CurrentUser,
    filter_date: date = Query(default_factory=date.today)
):
    """
    Dashboard uchun asosiy ko'rsatkichlar.
    Kunlik filter daromad (revenue) hisoblash uchun ishlatiladi.
    Qarz va ombor qiymatlari global hisoblanadi (shunday deb qabul qilamiz).
    """
    # 1. Jami qarz (Mijozlar qarzi) - debt_type = 'receive'
    def get_receive_debt():
        try:
            res = db.table("debts").select("remaining_amount").eq("status", "active").eq("debt_type", "receive").execute()
            res_part = db.table("debts").select("remaining_amount").eq("status", "partially_paid").eq("debt_type", "receive").execute()
            return sum(d.get("remaining_amount", 0) for d in res.data + res_part.data)
        except Exception:
            return 0

    # 2. Bizning qarz (Bizning ta'minotchilarga) - debt_type = 'pay'
    def get_pay_debt():
        try:
            res = db.table("debts").select("remaining_amount").eq("status", "active").eq("debt_type", "pay").execute()
            res_part = db.table("debts").select("remaining_amount").eq("status", "partially_paid").eq("debt_type", "pay").execute()
            return sum(d.get("remaining_amount", 0) for d in res.data + res_part.data)
        except Exception:
            return 0

    # 3. Ombor qoldig'i summasi
    # ingredientlardagi cost_per_unit va inventory_stock.quantity ni ko'paytiramiz
    def get_inventory_value():
        # Joins: inventory_stock -> ingredients
        # In Supabase python client doing nested select can be tricky if not set up properly.
        # Let's fetch stock, then ingredients? Or we can just do a select("quantity, ingredients(cost_per_unit)")
        try:
            res = db.table("inventory_stock").select("quantity, ingredients(cost_per_unit)").execute()
            total = 0
            for item in res.data:
                qty = item.get("quantity", 0) or 0
                cost = 0
                if item.get("ingredients") and isinstance(item["ingredients"], dict):
                    cost = item["ingredients"].get("cost_per_unit", 0) or 0
                total += qty * cost
            return total
        except Exception:
            # Fallback if the join fails
            return 0

    # 4. Filter qilingan sanadagi Daromad (Revenue)
    def get_revenue():
        try:
            q = db.table("daily_reports").select("total_revenue").eq("report_date", filter_date.isoformat())
            if current_user["role"] == "manager":
                q = q.eq("created_by", current_user["id"])
            res = q.execute()
            return sum(d.get("total_revenue", 0) or 0 for d in res.data)
        except Exception:
            return 0

    with ThreadPoolExecutor(max_workers=4) as executor:
        f1 = executor.submit(get_receive_debt)
        f2 = executor.submit(get_pay_debt)
        f3 = executor.submit(get_inventory_value)
        f4 = executor.submit(get_revenue)
        
        total_receive = f1.result()
        total_pay = f2.result()
        total_inventory = f3.result()
        total_revenue = f4.result()

    return {
        "date": filter_date.isoformat(),
        "total_receive_debt": total_receive,
        "total_pay_debt": total_pay,
        "total_inventory_value": total_inventory,
        "total_revenue": total_revenue
    }
