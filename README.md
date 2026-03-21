# 🍽️ Restoran Boshqaruv Tizimi

**Python FastAPI + Supabase + Telegram Mini App**

AI yordamida screenshot, audio va Excel dan avtomatik hisobot tahlili.

---

## 📁 Loyiha Tuzilishi

```
restoran/
├── backend/
│   ├── app/
│   │   ├── api/v1/      # Endpoint routerlar
│   │   ├── core/        # Config, Security, DB, Deps
│   │   ├── models/      # Pydantic schemas
│   │   └── services/    # Business logic
│   ├── supabase/
│   │   └── schema.sql   # Database schema
│   ├── .env             # Environment o'zgaruvchilar
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── api/         # Axios client
│   │   ├── pages/       # Barcha sahifalar
│   │   ├── components/  # NavBar va boshqalar
│   │   └── store/       # Zustand state
│   └── Dockerfile
└── docker-compose.yml
```

---

## ⚡ Ishga Tushirish (2 qadam)

### 1️⃣ Environment sozlash

```bash
cd backend
cp .env.example .env
# .env faylini oching va qiymatlarni kiriting
```

**`.env` da to'ldirish kerak:**
| O'zgaruvchi | Qayerdan olish |
|---|---|
| `SUPABASE_URL` | Supabase → Settings → API |
| `SUPABASE_ANON_KEY` | Supabase → Settings → API |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase → Settings → API |
| `JWT_SECRET_KEY` | Ixtiyoriy uzun string (32+ belgi) |
| `TELEGRAM_BOT_TOKEN` | @BotFather dan |
| `OPENAI_API_KEY` | platform.openai.com |
| `ESKIZ_EMAIL` | eskiz.uz hisob |
| `ESKIZ_PASSWORD` | eskiz.uz parol |

### 2️⃣ Database schema yuklash

Supabase → SQL Editor → quyidagini joylashtiring:
```
backend/supabase/schema.sql
```

---

## 🚀 Ishga Tushirish

### Docker bilan (tavsiya etiladi)
```bash
docker-compose up --build
```
- Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Frontend: http://localhost:5173

### Qo'lda
```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend (boshqa terminal)
cd frontend
npm install
npm run dev
```

---

## 🤖 AI Parsing qanday ishlaydi?

1. **Screenshot** → GPT-4o Vision → Mahsulot va narxlar ajratiladi
2. **Audio** → Whisper STT → O'zbekcha transkripsiya → GPT-4o strukturalaydi
3. **Excel** → pandas → Ustun mapping → Mahsulot nomlari moslashtirish (rapidfuzz)
4. Har uch holatda ham: AI natija → **Foydalanuvchi tasdiqlaydi** → DB ga saqlanadi

---

## 🔐 Autentifikatsiya

- Telegram WebApp `initData` HMAC-SHA256 bilan tekshiriladi
- JWT Access Token (60 daqiqa) + Refresh Token (30 kun)
- Rollar: `super_user` va `manager`

---

## 📱 Telegram Mini App sozlash

1. @BotFather → `/newbot` → Token oling
2. `/newapp` → URL: `https://your-frontend.com`
3. Super User qo'shish: Admin Panel → `telegram_id` kiriting

---

## 📊 API Endpoints

| Module | Prefix | Asosiy Operatsiyalar |
|---|---|---|
| Auth | `/api/v1/auth` | login, refresh |
| Reports | `/api/v1/reports` | CRUD, submit, approve |
| Sales | `/api/v1/sales` | create, bulk, delete |
| Expenses | `/api/v1/expenses` | create, list, delete |
| Inventory | `/api/v1/inventory` | stock, receipts, variance |
| Debts | `/api/v1/debts` | create, payments, SMS |
| AI | `/api/v1/ai` | screenshot, audio, excel |
| Export | `/api/v1/export` | excel, pdf |
| Admin | `/api/v1/admin` | users, products, ingredients |

Full dokumentatsiya: `http://localhost:8000/docs`
"# SAC_BOT_V1.2" 
