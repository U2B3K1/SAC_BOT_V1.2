from fastapi import APIRouter

from app.api.v1 import auth, debts, inventory, reports, sales

router = APIRouter()

router.include_router(auth.router, prefix="/v1/auth", tags=["auth"])
router.include_router(debts.router, prefix="/v1/debts", tags=["debts"])
router.include_router(inventory.router, prefix="/v1/inventory", tags=["inventory"])
router.include_router(reports.router, prefix="/v1/reports", tags=["reports"])
router.include_router(sales.router, prefix="/v1/sales", tags=["sales"])