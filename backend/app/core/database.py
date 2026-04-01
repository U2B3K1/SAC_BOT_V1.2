from supabase import create_client, Client
from app.core.config import settings
from functools import lru_cache

# =============================================
# Singleton Supabase clients (cached)
# Har safar yangi connection yaratmaslik uchun
# =============================================

@lru_cache(maxsize=1)
def _create_anon_client() -> Client:
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)


@lru_cache(maxsize=1)
def _create_admin_client() -> Client:
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


def get_supabase() -> Client:
    """Supabase client (anon key - RLS ishlaydi) - cached singleton"""
    return _create_anon_client()


def get_supabase_admin() -> Client:
    """Supabase admin client (service role - RLS bypass) - cached singleton"""
    return _create_admin_client()
