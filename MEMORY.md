# 🧠 Project Memory: SAC_BOT_V1.2

Ushbu fayl loyihaning joriy holati, muhim texnik qarorlar va o'zgarishlarni saqlaydi.

## 📍 Joriy Holat (Current Status - 2026-04-06)
- **Backend:** FastAPI + Supabase (PostgreSQL). Buxgalteriya va FIFO logikasi SQL qatlamiga (RPC) o'tkazildi.
- **Frontend:** React + Zustand. Offline-first kesh tizimi joriy etildi.
- **Security:** Telegram `initData` hmac-sha256 orqali qat'iy tekshiriladi.
- **AI Tizimi:** Parsing natijalari avval `pending_actions` staging jadvaliga tushadi.

## 🏗️ Muhim Texnik Qarorlar (Key Architecture Decisions)
- **Double-Entry Accounting:** Har bir tranzaksiya `ledger_entries` jadvalida Debet/Kredit qoidasi bo'yicha aks etadi. Bu balansni 100% aniq saqlashga xizmat qiladi.
- **FIFO Inventory:** Tovar tannarxi eng birinchi kirgan partiya narxidan kelib chiqib hisoblanadi (`inventory_batches`).
- **Atomic Transactions:** Stok yangilanishi, qarz yaratish va ledger yozuvlari bitta SQL RPC (`process_sale_fifo`, `process_inventory_receipt`) ichida bajariladi.
- **Offline Sync:** Internet uzilgan holatda foydalanuvchi amallari `useSyncStore` (Zustand + Persist) orqali saqlanadi va internet tiklanganda serverga yuboriladi.

## 🛠️ Amalga Oshirilgan Milestones (Senior Overhaul)
- [x] **Database:** Ledger, Inventory Batches va Pending Actions jadvallari qo'shildi.
- [x] **Backend:** Atomic RPC chaqiruvlari uchun API endpointlari yangilandi.
- [x] **Security:** Telegram auth middleware (`validate_telegram_init`) integratsiya qilindi.
- [x] **Sync:** Frontend uchun offline-first kesh tizimi yaratildi.

## 📝 Eslatmalar
- Supabase'da yangi SQL migration (`migration_04`) albatta bajarilgan bo'lishi shart.
- `requirements.txt` da `openpyxl` va `et-xmlfile` mavjudligiga ishonch hosil qiling (Excel export uchun).
- Har doim `app.main:app` entry point sifatida ishlatiladi (Railway/Vercel uchun).

---
*Oxirgi yangilanish: 2026-04-06 (Senior Overhaul Phase)*
