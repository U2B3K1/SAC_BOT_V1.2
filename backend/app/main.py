from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time

from app.core.config import settings
from app.api.v1 import auth, admin, reports, sales, expenses, inventory, debts, ai, export

from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"status": "ok"}

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
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
async def root():
    return {
        "status": "✅ Ishlayapti",
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    from app.core.database import get_supabase_admin
    try:
        db = get_supabase_admin()
        db.table("departments").select("id").limit(1).execute()
        db_status = "✅ Ulangan"
    except Exception as e:
        db_status = f"❌ Xato: {str(e)}"

    return {
        "status": "ok",
        "database": db_status,
        "app": settings.APP_NAME,
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












