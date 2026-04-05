from app.core.database import get_supabase_admin
import uuid

def test_rpc():
    db = get_supabase_admin()
    print("🔍 RPC test boshlandi...")
    
    try:
        # 1. Departments dan bitta ID olish
        dep = db.table("departments").select("id").limit(1).execute()
        if not dep.data:
            print("❌ Departments bo'sh!")
            return
        dep_id = dep.data[0]['id']
        
        # 2. Users dan bitta ID olish
        user = db.table("users").select("id").limit(1).execute()
        if not user.data:
            print("❌ Users bo'sh!")
            return
        user_id = user.data[0]['id']

        print(f"✅ Dep ID: {dep_id}, User ID: {user_id}")
        
        # 3. Simple RPC chaqiruvi (test uchun)
        # Bu yerda biz yangi jadvallarni shunchaki select qilib ko'ramiz
        print("🔍 Yangi jadvallarni tekshirish...")
        db.table("ledger_entries").select("id").limit(1).execute()
        print("✅ ledger_entries OK")
        db.table("inventory_batches").select("id").limit(1).execute()
        print("✅ inventory_batches OK")
        db.table("pending_actions").select("id").limit(1).execute()
        print("✅ pending_actions OK")
        
        print("🎉 Baza strukturasi muvaffaqiyatli tekshirildi!")
        
    except Exception as e:
        print(f"❌ Xatolik aniqlandi: {str(e)}")

if __name__ == "__main__":
    test_rpc()
