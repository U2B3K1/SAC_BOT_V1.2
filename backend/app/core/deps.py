from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import time

from app.core.security import decode_token, verify_telegram_init_data
from app.core.database import get_supabase_admin

security = HTTPBearer()

# =============================================
# In-memory user cache (TTL: 60 soniya)
# Har so'rovda DB query yuborishni oldini oladi
# =============================================
_user_cache: dict[str, tuple[dict, float]] = {}
_USER_CACHE_TTL = 60  # sekund


def _get_cached_user(user_id: str) -> dict | None:
    """Cache dan foydalanuvchini olish (TTL bilan)"""
    if user_id in _user_cache:
        user_data, cached_at = _user_cache[user_id]
        if time.time() - cached_at < _USER_CACHE_TTL:
            return user_data
        # Eskirgan — o'chirish
        del _user_cache[user_id]
    return None


def _set_cached_user(user_id: str, user_data: dict):
    """Foydalanuvchini cache ga saqlash"""
    # Cache hajmini cheklash (max 200 user)
    if len(_user_cache) > 200:
        oldest_key = min(_user_cache, key=lambda k: _user_cache[k][1])
        del _user_cache[oldest_key]
    _user_cache[user_id] = (user_data, time.time())


def invalidate_user_cache(user_id: str):
    """User o'zgarganda cache ni tozalash (update/deactivate da chaqirish)"""
    _user_cache.pop(user_id, None)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]
) -> dict:
    """JWT tokendan joriy foydalanuvchini olish — cache bilan optimized"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Avtorizatsiya muvaffaqiyatsiz",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_token(credentials.credentials)
    if payload is None:
        raise credentials_exception

    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    # 1. Cache dan tekshirish (DB query yo'q!)
    cached_user = _get_cached_user(user_id)
    if cached_user:
        return cached_user

    # 2. Cache da yo'q — DB dan olish va cache ga saqlash
    db = get_supabase_admin()
    result = db.table("users").select("id, telegram_id, full_name, role, department_id, is_active").eq("id", user_id).eq("is_active", True).single().execute()
    if not result.data:
        raise credentials_exception

    _set_cached_user(user_id, result.data)
    return result.data


def require_super_user(current_user: Annotated[dict, Depends(get_current_user)]) -> dict:
    """Faqat super_user uchun"""
    if current_user.get("role") != "super_user":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu amal faqat Super User uchun ruxsat etilgan"
        )
    return current_user


def require_manager_or_above(current_user: Annotated[dict, Depends(get_current_user)]) -> dict:
    """Manager yoki super_user uchun"""
    if current_user.get("role") not in ["manager", "super_user"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ruxsat yo'q"
        )
    return current_user


def validate_telegram_init(init_data: str):
    """
    Telegram initData ni HMAC-SHA256 bilan qat'iy tekshirish.
    Middleware sifatida ishlatiladi.
    """
    tg_user = verify_telegram_init_data(init_data)
    if not tg_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Xavfsizlik tekshiruvi: Telegram ma'lumotlari haqiqiy emas"
        )
    return tg_user


# Type aliases
CurrentUser = Annotated[dict, Depends(get_current_user)]
SuperUser = Annotated[dict, Depends(require_super_user)]
ManagerUser = Annotated[dict, Depends(require_manager_or_above)]
