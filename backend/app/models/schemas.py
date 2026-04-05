from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, UUID4, field_validator
import uuid


# =============================================
# AUTH
# =============================================
class TelegramLoginRequest(BaseModel):
    init_data: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict  # {id, full_name, role, telegram_id, department_id}


class RefreshRequest(BaseModel):
    refresh_token: str


# =============================================
# USERS
# =============================================
class UserCreate(BaseModel):
    telegram_id: int
    full_name: str
    phone: Optional[str] = None
    role: str = "manager"
    department_id: Optional[str] = None

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    department_id: Optional[str] = None
    is_active: Optional[bool] = None


# =============================================
# DEPARTMENTS
# =============================================
class DepartmentCreate(BaseModel):
    name: str
    code: str
    sort_order: int = 0

class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


# =============================================
# PRODUCTS
# =============================================
class ProductCreate(BaseModel):
    department_id: str
    name: str
    name_aliases: List[str] = []
    unit: str = "porsiya"
    sale_price: float

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    name_aliases: Optional[List[str]] = None
    sale_price: Optional[float] = None
    is_active: Optional[bool] = None
    department_id: Optional[str] = None


# =============================================
# INGREDIENTS
# =============================================
class IngredientCreate(BaseModel):
    name: str
    unit: str
    cost_per_unit: float = 0.0

class IngredientUpdate(BaseModel):
    name: Optional[str] = None
    unit: Optional[str] = None
    cost_per_unit: Optional[float] = None
    is_active: Optional[bool] = None


# =============================================
# RECIPES
# =============================================
class RecipeIngredientItem(BaseModel):
    ingredient_id: str
    quantity: float
    unit: str

class RecipeCreate(BaseModel):
    product_id: str
    yield_kg: Optional[float] = None
    portions_per_kg: Optional[float] = None
    notes: Optional[str] = None
    ingredients: List[RecipeIngredientItem] = []

class RecipeUpdate(BaseModel):
    yield_kg: Optional[float] = None
    portions_per_kg: Optional[float] = None
    notes: Optional[str] = None
    ingredients: Optional[List[RecipeIngredientItem]] = None


# =============================================
# EXPENSE CATEGORIES
# =============================================
class ExpenseCategoryCreate(BaseModel):
    name: str
    code: str
    description: Optional[str] = None
    sort_order: int = 0


# =============================================
# DAILY REPORTS
# =============================================
class DailyReportCreate(BaseModel):
    report_date: date
    department_id: str
    opening_balance: float = 0.0
    notes: Optional[str] = None

class DailyReportUpdate(BaseModel):
    opening_balance: Optional[float] = None
    notes: Optional[str] = None


# =============================================
# SALES
# =============================================
class SaleCreate(BaseModel):
    daily_report_id: str
    product_id: str
    quantity: float
    unit_price: float
    input_method: str = "manual"
    notes: Optional[str] = None

    @field_validator("quantity", "unit_price")
    @classmethod
    def must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("Miqdor va narx musbat bo'lishi kerak")
        return v

class SalesBulkCreate(BaseModel):
    daily_report_id: str
    items: List[SaleCreate]


# =============================================
# EXPENSES
# =============================================
class ExpenseCreate(BaseModel):
    daily_report_id: str
    category_id: str
    amount: float
    description: Optional[str] = None
    input_method: str = "manual"

    @field_validator("amount")
    @classmethod
    def must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("Summa musbat bo'lishi kerak")
        return v


# =============================================
# INVENTORY
# =============================================
class InventoryReceiptItemCreate(BaseModel):
    ingredient_id: str
    quantity: float
    unit: str
    unit_cost: float

class InventoryReceiptCreate(BaseModel):
    receipt_date: date
    department_id: Optional[str] = None
    supplier: Optional[str] = None
    notes: Optional[str] = None
    is_paid: bool = True
    items: List[InventoryReceiptItemCreate]

class StockUpdateItem(BaseModel):
    ingredient_id: str
    actual_qty: float
    reason: Optional[str] = None


# =============================================
# DEBTS
# =============================================
class DebtCreate(BaseModel):
    debt_type: str = "receive"  # "receive" (haqdorlik) yoki "pay" (qarzimiz)
    debtor_name: str
    organization: Optional[str] = None
    phone: Optional[str] = None
    initial_amount: float
    description: Optional[str] = None
    debt_date: date
    due_date: Optional[date] = None
    notes: Optional[str] = None

class DebtPaymentCreate(BaseModel):
    amount: float
    payment_date: date
    notes: Optional[str] = None

class SMSRequest(BaseModel):
    debt_id: str
    custom_message: Optional[str] = None


# =============================================
# AI PARSE
# =============================================
class AIConfirmRequest(BaseModel):
    session_id: str
    confirmed_data: dict  # Tasdiqlangan yoki tahrir qilingan ma'lumot
    daily_report_id: Optional[str] = None


# =============================================
# PENDING ACTIONS
# =============================================
class PendingActionCreate(BaseModel):
    action_type: str  # 'sale', 'receipt', 'expense', 'adjustment'
    payload: dict
    notes: Optional[str] = None

class PendingActionConfirm(BaseModel):
    id: UUID4
    final_payload: Optional[dict] = None  # Foydalanuvchi tahrirlagan bo'lishi mumkin


# =============================================
# EXPORT
# =============================================
class ExportRequest(BaseModel):
    report_id: Optional[str] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    department_id: Optional[str] = None
    format: str = "excel"  # "excel" | "pdf"
