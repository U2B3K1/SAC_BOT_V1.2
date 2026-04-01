import httpx
import json
from typing import Optional
from app.core.config import settings

_eskiz_token: Optional[str] = None


def _get_eskiz_token() -> str:
    """Eskiz.uz dan token olish"""
    global _eskiz_token
    if _eskiz_token:
        return _eskiz_token

    with httpx.Client() as client:
        response = client.post(
            "https://notify.eskiz.uz/api/auth/login",
            data={"email": settings.ESKIZ_EMAIL, "password": settings.ESKIZ_PASSWORD}
        )
        data = response.json()
        _eskiz_token = data.get("data", {}).get("token")
        return _eskiz_token


def send_debt_reminder(phone: str, message: str) -> dict:
    """
    Eskiz.uz orqali SMS yuborish.
    Telefon formati: 998901234567 (+ belgisiz)
    """
    if not settings.ESKIZ_EMAIL or not settings.ESKIZ_PASSWORD:
        return {"status": "skipped", "reason": "SMS konfiguratsiya qilinmagan"}

    # Telefon raqamini tozalash
    clean_phone = phone.replace("+", "").replace(" ", "").replace("-", "")
    if not clean_phone.startswith("998"):
        clean_phone = "998" + clean_phone.lstrip("0")

    try:
        token = _get_eskiz_token()
        with httpx.Client() as client:
            response = client.post(
                "https://notify.eskiz.uz/api/message/sms/send",
                headers={"Authorization": f"Bearer {token}"},
                data={
                    "mobile_phone": clean_phone,
                    "message": message,
                    "from": settings.ESKIZ_SENDER_ID,
                    "callback_url": "",
                }
            )
        return response.json()
    except Exception as e:
        return {"status": "error", "reason": str(e)}


def send_bulk_sms(phones: list[str], message: str) -> list[dict]:
    """Ko'p raqamga SMS yuborish"""
    results = []
    for phone in phones:
        result = send_debt_reminder(phone, message)
        results.append({"phone": phone, **result})
    return results
