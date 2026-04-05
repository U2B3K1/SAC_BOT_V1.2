# 🧠 Project Memory: Restoran Boshqaruv Tizimi

Ushbu fayl loyihaning joriy holati, muhim texnik qarorlar va kelajakdagi rejalarini saqlaydi.

## 📍 Joriy Holat (Current Status)
- **Backend:** FastAPI + Supabase integratsiyasi tayyor.
- **Frontend:** React + Zustand + Telegram Mini App (TMA) muhiti sozlangan.
- **AI Tizimi:** Screenshot (Vision), Audio (Whisper) va Excel parsing modullari implementatsiya qilingan.
- **Oxirgi Milestones:** 
    - "Bizning qarz" (Debts) moduli integratsiyasi yakunlangan.
    - Real-time dashboard va moliyaviy hisobotlar tahlili yo'lga qo'yilgan.

## 🏗️ Arxitektura Qarorlari (Key Decisions)
- **Database:** Supabase real-time va auth imkoniyatlari uchun tanlangan.
- **AI Processing:** GPT-4o modelidan Vision va Strukturalash (json mode) uchun foydalaniladi.
- **State Management:** Frontendda soddalik va tezlik uchun Zustand tanlangan.
- **Sync Pattern:** AI Parsing natijalari avval foydalanuvchiga tasdiqlash uchun ko'rsatiladi ("Pending Approval"), so'ngra DB ga saqlanadi.

## 🛠️ Vazifalar (Open Tasks & Roadmap)
- [ ] Tizim unumdorligini optimallashtirish (Optimization).
- [ ] "Admin panel" orqali user rollarini boshqarishni kengaytirish.
- [ ] Export (PDF/Excel) hisobotlarni yanada boyitish.
- [ ] Ko'p bo'limli restoranlar uchun "Multi-branch" tizimini test qilish.

## 📝 Eslatmalar
- Telegram ID orqali autentifikatsiya qat'iy nazoratda turishi shart.
- `.env` faylidagi API keylar hecham commit qilinmasligi kerak.
- Har bir yangi endpoint `/api/v1/` prefiksi bilan boshlanishi lozim.

---
*Oxirgi yangilanish: 2026-04-03*
