from fastapi import APIRouter, HTTPException, status
from app.models.schemas import TelegramLoginRequest, RefreshRequest, TokenResponse
from app.core.security import (
    verify_telegram_init_data,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.core.database import get_supabase_admin

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/telegram", response_model=TokenResponse)
async def telegram_login(body: TelegramLoginRequest):
    """Telegram WebApp orqali tizimga kirish"""
    db = get_supabase_admin()

    # initData tekshirish
    tg_user = verify_telegram_init_data(body.init_data)
    if not tg_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Telegram ma'lumotlari noto'g'ri yoki muddati o'tgan"
        )

    telegram_id = tg_user.get("id")
    if not telegram_id:
        raise HTTPException(status_code=400, detail="Telegram ID topilmadi")

    # Foydalanuvchini DB dan qidirish
    result = db.table("users").select("*").eq("telegram_id", telegram_id).execute()

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Siz tizimga qo'shilmagan. Super User bilan bog'laning."
        )

    user = result.data[0]
    if not user.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hisobingiz o'chirilgan"
        )

    # Token yaratish
    token_data = {"sub": user["id"], "role": user["role"]}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user={
            "id": user["id"],
            "full_name": user["full_name"],
            "role": user["role"],
            "telegram_id": user["telegram_id"],
        }
    )


@router.post("/refresh")
async def refresh_token(body: RefreshRequest):
    """Access token ni refresh token bilan yangilash"""
    payload = decode_token(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Refresh token noto'g'ri")

    user_id = payload.get("sub")
    db = get_supabase_admin()
    result = db.table("users").select("id,role,is_active").eq("id", user_id).single().execute()

    if not result.data or not result.data.get("is_active"):
        raise HTTPException(status_code=401, detail="Foydalanuvchi topilmadi")

    user = result.data
    token_data = {"sub": user["id"], "role": user["role"]}
    return {
        "access_token": create_access_token(token_data),
        "token_type": "bearer"
    }


@router.get("/me")
async def get_me_test(init_data: str):
    """Test: Telegram init_data ni manual tekshirish"""
    user = verify_telegram_init_data(init_data)
    if not user:
        raise HTTPException(400, "Invalid init_data")
    return {"tg_user": user}
