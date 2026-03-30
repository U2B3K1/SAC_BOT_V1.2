from supabase import create_client, Client
from app.core.config import settings

_supabase_client: Client | None = None
_supabase_admin_client: Client | None = None


def get_supabase() -> Client:
    """Supabase client (anon key - RLS ishlaydi). Singleton — bir marta yaratiladi."""
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    return _supabase_client


def get_supabase_admin() -> Client:
    """Supabase admin client (service role - RLS bypass). Singleton — bir marta yaratiladi."""
    global _supabase_admin_client
    if _supabase_admin_client is None:
        _supabase_admin_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
    return _supabase_admin_client
