from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

try:
    supabase = create_client(url, key)
    response = supabase.table("products").select("count", count="exact").limit(1).execute()
    print("✅ Muvaffaqiyatli ulanish! Mahsulotlar soni:", response.count)
except Exception as e:
    print("❌ Xatolik yuz berdi:", str(e))
