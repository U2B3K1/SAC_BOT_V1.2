import json
import io
import base64
from typing import Optional
from openai import AsyncOpenAI
from app.core.config import settings
from app.core.database import get_supabase_admin
import httpx
import pandas as pd

db = get_supabase_admin()
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


def _get_products_context() -> str:
    """Mavjud mahsulotlar ro'yxatini AI uchun kontekst sifatida tayyorlash"""
    products = db.table("products").select(
        "name, name_aliases, sale_price, departments(name)"
    ).eq("is_active", True).execute()

    lines = []
    for p in products.data or []:
        aliases = ", ".join(p.get("name_aliases") or [])
        dept = p.get("departments", {}).get("name", "")
        lines.append(f"- {p['name']} ({dept}): {p['sale_price']} so'm{', Sinonimlar: ' + aliases if aliases else ''}")

    return "\n".join(lines) if lines else "Mahsulotlar kiritilmagan"


async def parse_screenshot(session_id: str, file_url: str):
    """GPT-4o Vision bilan screenshot tahlili"""
    try:
        # Rasmni URL dan yuklab olish
        async with httpx.AsyncClient() as http:
            img_response = await http.get(file_url)
        img_bytes = img_response.content
        img_b64 = base64.b64encode(img_bytes).decode("utf-8")

        products_ctx = _get_products_context()

        prompt = f"""Bu restoran kassasidan olingan sotuv screenshotidir.
Quyidagi JSON formatda ma'lumot chiqar:
{{
  "date": "YYYY-MM-DD yoki null",
  "items": [
    {{"product_name": "...", "quantity": 0.0, "unit_price": 0.0}}
  ],
  "total": 0.0,
  "notes": "qo'shimcha izoh (agar bo'lsa)"
}}

Mavjud mahsulotlar ro'yxati:
{products_ctx}

QOIDALAR:
1. Mahsulot nomlarini ro'yxatdagi eng yaqin nomga moslashtirishga harakat qiling
2. Agar moslik topilmasa, screenshotdagi asl nomni qoldiring
3. Miqdor va narxlarni aniq o'qing
4. Faqat JSON qaytaring, boshqa matn yo'q"""

        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                    ],
                }
            ],
            max_tokens=2000,
        )

        raw_output = response.choices[0].message.content
        # JSON ni tozalash
        json_str = raw_output.strip()
        if "```json" in json_str:
            json_str = json_str.split("```json")[1].split("```")[0].strip()
        elif "```" in json_str:
            json_str = json_str.split("```")[1].split("```")[0].strip()

        parsed = json.loads(json_str)

        # Mahsulot ID larini topish
        items_with_ids = await _match_product_names(parsed.get("items", []))
        parsed["items"] = items_with_ids

        db.table("ai_parse_sessions").update({
            "status": "pending",
            "raw_ai_output": {"raw": raw_output},
            "parsed_data": parsed,
        }).eq("id", session_id).execute()

    except Exception as e:
        db.table("ai_parse_sessions").update({
            "status": "pending",
            "error_message": str(e),
            "parsed_data": {},
        }).eq("id", session_id).execute()


async def parse_audio(session_id: str, file_url: str):
    """OpenAI Whisper bilan audio transkripsiya"""
    try:
        async with httpx.AsyncClient() as http:
            audio_response = await http.get(file_url)
        audio_bytes = audio_response.content

        # Whisper bilan o'zbek tilida transkripsiya
        transcript = await client.audio.transcriptions.create(
            model="whisper-1",
            file=("audio.ogg", io.BytesIO(audio_bytes), "audio/ogg"),
            language="uz",
        )
        text = transcript.text

        # GPT bilan strukturali ma'lumot chiqarish
        products_ctx = _get_products_context()
        prompt = f"""Quyidagi ovozli ma'lumotdan restoran xarajati yoki qoldiq kiritish uchun strukturali ma'lumot chiqar.
Matn: "{text}"

Xarajat bo'lsa qaytaruvchi format:
{{"type": "expense", "category": "gel|bunaga|osvijitel|ishchi_haqi|elektr|boshqa", "amount": 0.0, "description": "..."}}

Qoldiq bo'lsa:
{{"type": "stock", "ingredient_name": "...", "quantity": 0.0, "unit": "kg|litr|dona"}}

Sotuv bo'lsa:
{{"type": "sales", "items": [{{"product_name": "...", "quantity": 0.0, "unit_price": 0.0}}]}}

Faqat JSON qaytaring."""

        gpt_response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
        )
        raw_output = gpt_response.choices[0].message.content
        json_str = raw_output.strip().replace("```json", "").replace("```", "").strip()
        parsed = json.loads(json_str)
        parsed["transcript"] = text

        db.table("ai_parse_sessions").update({
            "status": "pending",
            "raw_ai_output": {"transcript": text, "raw": raw_output},
            "parsed_data": parsed,
        }).eq("id", session_id).execute()

    except Exception as e:
        db.table("ai_parse_sessions").update({
            "status": "pending",
            "error_message": str(e),
            "parsed_data": {},
        }).eq("id", session_id).execute()


async def parse_excel_file(session_id: str, file_content: bytes):
    """pandas bilan Excel faylni tahlil qilish"""
    try:
        df = pd.read_excel(io.BytesIO(file_content))

        # Ustun nomlarini kichik harfga o'girish va tozalash
        df.columns = [str(c).lower().strip() for c in df.columns]
        df = df.fillna(0)

        # Ustun mapping (turli formatlardagi Excel fayllar uchun)
        column_aliases = {
            "mahsulot": ["mahsulot", "product", "tovar", "nomi", "name"],
            "miqdor": ["miqdor", "qty", "quantity", "soni", "count"],
            "narx": ["narx", "price", "unit_price", "summa", "amount"],
        }

        def find_column(aliases: list) -> Optional[str]:
            for col in df.columns:
                if any(alias in col for alias in aliases):
                    return col
            return None

        name_col = find_column(column_aliases["mahsulot"])
        qty_col = find_column(column_aliases["miqdor"])
        price_col = find_column(column_aliases["narx"])

        if not name_col:
            raise ValueError("'Mahsulot' yoki 'product' ustuni topilmadi")

        items = []
        for _, row in df.iterrows():
            name = str(row.get(name_col, "")).strip()
            if not name or name == "0":
                continue
            item = {
                "product_name": name,
                "quantity": float(row.get(qty_col, 1)) if qty_col else 1.0,
                "unit_price": float(row.get(price_col, 0)) if price_col else 0.0,
            }
            items.append(item)

        items_with_ids = await _match_product_names(items)
        parsed = {"items": items_with_ids, "total_rows": len(items)}

        db.table("ai_parse_sessions").update({
            "status": "pending",
            "raw_ai_output": {"columns": list(df.columns), "rows": len(df)},
            "parsed_data": parsed,
        }).eq("id", session_id).execute()

    except Exception as e:
        db.table("ai_parse_sessions").update({
            "status": "pending",
            "error_message": str(e),
            "parsed_data": {},
        }).eq("id", session_id).execute()


async def _match_product_names(items: list) -> list:
    """Mahsulot nomlarini DB dagi nomlar bilan moslashtirish"""
    try:
        from rapidfuzz import process, fuzz
    except ImportError:
        return items

    products = db.table("products").select("id, name, name_aliases, sale_price").eq("is_active", True).execute()
    product_map = {}
    all_names = []
    for p in products.data or []:
        product_map[p["name"]] = p
        all_names.append(p["name"])
        for alias in (p.get("name_aliases") or []):
            product_map[alias] = p
            all_names.append(alias)

    enriched = []
    for item in items:
        name = item.get("product_name", "")
        # Exact match
        if name in product_map:
            p = product_map[name]
            item["product_id"] = p["id"]
            item["matched_name"] = p["name"]
            item["confidence"] = 100
        else:
            # Fuzzy match
            match = process.extractOne(name, all_names, scorer=fuzz.WRatio, score_cutoff=70)
            if match:
                p = product_map[match[0]]
                item["product_id"] = p["id"]
                item["matched_name"] = p["name"]
                item["confidence"] = match[1]
            else:
                item["product_id"] = None
                item["matched_name"] = None
                item["confidence"] = 0
                item["needs_review"] = True

        enriched.append(item)
    return enriched
