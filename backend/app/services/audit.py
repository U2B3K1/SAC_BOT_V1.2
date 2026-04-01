from app.core.database import get_supabase_admin
from typing import Optional
import threading


def _write_audit_log(
    user_id: str,
    table_name: str,
    record_id: Optional[str],
    action: str,
    old_data: Optional[dict],
    new_data: Optional[dict],
    ip_address: Optional[str],
):
    """Audit log ni DB ga yozish (background thread da)"""
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


def log_audit(
    user_id: str,
    table_name: str,
    record_id: Optional[str],
    action: str,
    old_data: Optional[dict],
    new_data: Optional[dict],
    ip_address: Optional[str] = None,
):
    """
    Harakat tarixini audit_logs jadvaliga yozish.
    Background thread da ishlaydi — asosiy response ni blokirovka QILMAYDI.
    """
    t = threading.Thread(
        target=_write_audit_log,
        args=(user_id, table_name, record_id, action, old_data, new_data, ip_address),
        daemon=True,
    )
    t.start()
