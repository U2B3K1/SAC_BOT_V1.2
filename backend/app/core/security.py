import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import unquote

from jose import JWTError, jwt

from app.core.config import settings


# =============================================
# TELEGRAM initData TEKSHIRISH
# =============================================

def verify_telegram_init_data(init_data: str) -> Optional[dict]:
    """
    Telegram WebApp initData ni HMAC-SHA256 bilan tekshirish.
    Haqiqiy bo'lsa user dict qaytaradi, aks holda None.
    """
    try:
        from urllib.parse import parse_qsl
        
        # initData da %7B kabi URL-encoded belgilar bo'ladi.
        # urllib.parse.parse_qsl ularni avtomatik decode qilib (oddiy matnga o'girib) key-value juftligini yaratadi!
        parsed_data = dict(parse_qsl(init_data))
        
        received_hash = parsed_data.pop("hash", None)
        if not received_hash:
            return None

        # auth_date tekshirish (24 soatdan eski bo'lmasin)
        auth_date = int(parsed_data.get("auth_date", 0))
        if time.time() - auth_date > 86400:  # 24 soat
            return None

        # Data string yaratish: decode qilingan qiymatlar bilan
        data_check_string = "\n".join(
            f"{k}={v}" for k, v in sorted(parsed_data.items())
        )

        # HMAC hisoblash
        secret_key = hmac.new(
            b"WebAppData",
            settings.TELEGRAM_BOT_TOKEN.encode(),
            hashlib.sha256
        ).digest()

        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(calculated_hash, received_hash):
            return None

        # User ma'lumotini parse qilish (parse_qsl orqali allaqachon '{' larga decode qilingan json olinadi)
        user_data = parsed_data.get("user", "{}")
        return json.loads(user_data)

    except Exception:
        return None


# =============================================
# JWT TOKEN YARATISH VA TEKSHIRISH
# =============================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        return None
