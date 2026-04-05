from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time

from app.core.config import settings
from app.api.v1 import auth, admin, reports, sales, expenses, inventory, debts, ai, export, dashboard


app = FastAPI(
    title=settings.APP_NAME,
    description="Restoran Boshqaruv Tizimi — Backend API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    from app.core.database import get_supabase_admin
    print("🚀 Server ishga tushmoqda...")
    try:
        db = get_supabase_admin()
        db.table("departments").select("id").limit(1).execute()
        print("✅ Supabase aloqasi muvaffaqiyatli o'rnatildi!")
    except Exception as e:
        print(f"❌ Supabase aloqasida xatolik: {str(e)}")

# =============================================
# MIDDLEWARE
# =============================================
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(round(process_time * 1000, 2)) + "ms"
    return response


# =============================================
# ROUTERLAR
# =============================================
API_PREFIX = "/api/v1"

app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(dashboard.router, prefix=API_PREFIX)
app.include_router(admin.router, prefix=API_PREFIX)
app.include_router(reports.router, prefix=API_PREFIX)
app.include_router(sales.router, prefix=API_PREFIX)
app.include_router(expenses.router, prefix=API_PREFIX)
app.include_router(inventory.router, prefix=API_PREFIX)
app.include_router(debts.router, prefix=API_PREFIX)
app.include_router(ai.router, prefix=API_PREFIX)
app.include_router(export.router, prefix=API_PREFIX)


# =============================================
# HEALTH CHECK
# =============================================
@app.get("/", tags=["Health"])
def root():
    return {
        "status": "✅ Ishlayapti",
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
def health_check():
    from app.core.database import get_supabase_admin
    try:
        db = get_supabase_admin()
        db.table("departments").select("id").limit(1).execute()
        db_status = "✅ Ulangan"
    except Exception as e:
        db_status = f"❌ Xato: {str(e)}"

    # Telegram Token tekshiruvi (xavfsizlik uchun faqat true/false)
    tg_token_status = "✅ O'rnatilgan" if settings.TELEGRAM_BOT_TOKEN else "❌ O'rnatilmagan"

    return {
        "status": "ok",
        "database": db_status,
        "telegram_token": tg_token_status,
        "app": settings.APP_NAME,
    }

@app.get("/debug/env", tags=["Health"])
def debug_env():
    """Railway o'zgaruvchilarini tekshirish (shifrlangan)"""
    def mask(s: str):
        if not s: return "❌ Yo'q"
        return f"{s[:4]}...{s[-4:]}" if len(s) > 8 else "***"

    return {
        "supabase_url": mask(settings.SUPABASE_URL),
        "telegram_token_present": bool(settings.TELEGRAM_BOT_TOKEN),
        "telegram_token_masked": mask(settings.TELEGRAM_BOT_TOKEN),
        "openai_key_present": bool(settings.OPENAI_API_KEY),
        "allowed_origins": settings.ALLOWED_ORIGINS,
    }


# =============================================
# XATOLIK ISHLOVCHILARI
# =============================================
@app.exception_handler(404)
async def not_found(request: Request, exc):
    return JSONResponse(status_code=404, content={"detail": "Topilmadi"})


@app.exception_handler(500)
async def server_error(request: Request, exc):
    return JSONResponse(status_code=500, content={"detail": "Server xatosi"})












