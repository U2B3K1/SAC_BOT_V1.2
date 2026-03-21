from typing import Annotated, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.security import decode_token
from app.core.database import get_supabase_admin

security = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]
) -> dict:
    """JWT tokendan joriy foydalanuvchini olish"""
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

    # DB dan foydalanuvchini tekshirish
    db = get_supabase_admin()
    result = db.table("users").select("*").eq("id", user_id).eq("is_active", True).single().execute()
    if not result.data:
        raise credentials_exception

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


# Type aliases
CurrentUser = Annotated[dict, Depends(get_current_user)]
SuperUser = Annotated[dict, Depends(require_super_user)]
ManagerUser = Annotated[dict, Depends(require_manager_or_above)]
