from app.core.database import get_supabase_admin
from typing import Optional


async def log_audit(
    user_id: str,
    table_name: str,
    record_id: Optional[str],
    action: str,
    old_data: Optional[dict],
    new_data: Optional[dict],
    ip_address: Optional[str] = None,
):
    """Harakat tarixini audit_logs jadvaliga yozish"""
    try:
        db = get_supabase_admin()
        db.table("audit_logs").insert({
            "user_id": user_id,
            "table_name": table_name,
            "record_id": record_id,
            "action": action,
            "old_data": old_data,
            "new_data": new_data,
            "ip_address": ip_address,
        }).execute()
    except Exception:
        pass  # Audit log muvaffaqiyatsiz bo'lsa asosiy amal davom etaversin
