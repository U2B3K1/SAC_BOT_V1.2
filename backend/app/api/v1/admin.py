from fastapi import APIRouter, HTTPException
from app.core.deps import CurrentUser, SuperUser, invalidate_user_cache
from app.core.database import get_supabase_admin
from app.models.schemas import (
    UserCreate, UserUpdate,
    DepartmentCreate, DepartmentUpdate,
    ProductCreate, ProductUpdate,
    IngredientCreate, IngredientUpdate,
    RecipeCreate, RecipeUpdate,
    ExpenseCategoryCreate,
)
from app.services.audit import log_audit
from app.services.calculation import invalidate_recipe_cache

router = APIRouter(prefix="/admin", tags=["Admin (Super User)"])

db = get_supabase_admin()


# =============================================
# USERS
# =============================================
@router.get("/users")
def list_users(current_user: SuperUser):
    result = db.table("users").select("*, departments(name, code)").order("created_at").execute()
    return result.data


@router.post("/users", status_code=201)
def create_user(body: UserCreate, current_user: SuperUser):
    # Mavjudligini tekshirish
    existing = db.table("users").select("id").eq("telegram_id", body.telegram_id).execute()
    if existing.data:
        raise HTTPException(400, "Bu Telegram ID allaqachon mavjud")

    data = body.model_dump()
    data["created_by"] = current_user["id"]
    result = db.table("users").insert(data).execute()
    log_audit(current_user["id"], "users", result.data[0]["id"], "INSERT", None, result.data[0])
    return result.data[0]


@router.patch("/users/{user_id}")
def update_user(user_id: str, body: UserUpdate, current_user: SuperUser):
    old = db.table("users").select("*").eq("id", user_id).single().execute()
    if not old.data:
        raise HTTPException(404, "Foydalanuvchi topilmadi")
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    result = db.table("users").update(updates).eq("id", user_id).execute()
    log_audit(current_user["id"], "users", user_id, "UPDATE", old.data, result.data[0])
    invalidate_user_cache(user_id)  # Cache tozalash
    return result.data[0]


@router.delete("/users/{user_id}")
def deactivate_user(user_id: str, current_user: SuperUser):
    if user_id == current_user["id"]:
        raise HTTPException(400, "O'zingizni o'chira olmaysiz")
    old = db.table("users").select("*").eq("id", user_id).single().execute()
    result = db.table("users").update({"is_active": False}).eq("id", user_id).execute()
    log_audit(current_user["id"], "users", user_id, "UPDATE", old.data, result.data[0])
    invalidate_user_cache(user_id)  # Cache tozalash
    return {"message": "Foydalanuvchi o'chirildi"}


# =============================================
# DEPARTMENTS
# =============================================
@router.get("/departments")
def list_departments(current_user: CurrentUser):
    result = db.table("departments").select("*").order("sort_order").execute()
    return result.data


@router.post("/departments", status_code=201)
def create_department(body: DepartmentCreate, current_user: SuperUser):
    result = db.table("departments").insert(body.model_dump()).execute()
    return result.data[0]


@router.patch("/departments/{dept_id}")
def update_department(dept_id: str, body: DepartmentUpdate, current_user: SuperUser):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    result = db.table("departments").update(updates).eq("id", dept_id).execute()
    return result.data[0]


# =============================================
# PRODUCTS
# =============================================
@router.get("/products")
def list_products(current_user: CurrentUser, department_id: str = None):
    q = db.table("products").select("*, departments(name,code)").eq("is_active", True)
    if department_id:
        q = q.eq("department_id", department_id)
    result = q.order("name").execute()
    return result.data


@router.post("/products", status_code=201)
def create_product(body: ProductCreate, current_user: SuperUser):
    result = db.table("products").insert(body.model_dump()).execute()
    log_audit(current_user["id"], "products", result.data[0]["id"], "INSERT", None, result.data[0])
    return result.data[0]


@router.patch("/products/{product_id}")
def update_product(product_id: str, body: ProductUpdate, current_user: SuperUser):
    old = db.table("products").select("*").eq("id", product_id).single().execute()
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    result = db.table("products").update(updates).eq("id", product_id).execute()
    log_audit(current_user["id"], "products", product_id, "UPDATE", old.data, result.data[0])
    return result.data[0]


@router.delete("/products/{product_id}")
def deactivate_product(product_id: str, current_user: SuperUser):
    result = db.table("products").update({"is_active": False}).eq("id", product_id).execute()
    return {"message": "Mahsulot o'chirildi"}


# =============================================
# INGREDIENTS
# =============================================
@router.get("/ingredients")
def list_ingredients(current_user: CurrentUser):
    result = db.table("ingredients").select("*").eq("is_active", True).order("name").execute()
    return result.data


@router.post("/ingredients", status_code=201)
def create_ingredient(body: IngredientCreate, current_user: SuperUser):
    result = db.table("ingredients").insert(body.model_dump()).execute()
    return result.data[0]


@router.patch("/ingredients/{ingredient_id}")
def update_ingredient(ingredient_id: str, body: IngredientUpdate, current_user: SuperUser):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    result = db.table("ingredients").update(updates).eq("id", ingredient_id).execute()
    return result.data[0]


# =============================================
# RECIPES
# =============================================
@router.get("/recipes")
def list_recipes(current_user: CurrentUser):
    result = db.table("recipes").select(
        "*, products(name, sale_price), recipe_ingredients(quantity, unit, ingredients(name, unit, cost_per_unit))"
    ).execute()
    return result.data


@router.post("/recipes", status_code=201)
def create_recipe(body: RecipeCreate, current_user: SuperUser):
    # Recipe asosiy
    recipe_data = {
        "product_id": body.product_id,
        "yield_kg": body.yield_kg,
        "portions_per_kg": body.portions_per_kg,
        "notes": body.notes,
    }
    recipe_result = db.table("recipes").insert(recipe_data).execute()
    recipe_id = recipe_result.data[0]["id"]

    # Ingredientlarni qo'shish
    if body.ingredients:
        items = [{"recipe_id": recipe_id, **item.model_dump()} for item in body.ingredients]
        db.table("recipe_ingredients").insert(items).execute()

    return db.table("recipes").select(
        "*, recipe_ingredients(*, ingredients(name,unit))"
    ).eq("id", recipe_id).single().execute().data


@router.patch("/recipes/{recipe_id}")
def update_recipe(recipe_id: str, body: RecipeUpdate, current_user: SuperUser):
    updates = {k: v for k, v in body.model_dump(exclude={"ingredients"}).items() if v is not None}
    if updates:
        db.table("recipes").update(updates).eq("id", recipe_id).execute()

    if body.ingredients is not None:
        # O'chirish va qayta qo'shish
        db.table("recipe_ingredients").delete().eq("recipe_id", recipe_id).execute()
        if body.ingredients:
            items = [{"recipe_id": recipe_id, **item.model_dump()} for item in body.ingredients]
            db.table("recipe_ingredients").insert(items).execute()

    # Recipe o'zgardi — barcha product cost cache ni tozalash
    invalidate_recipe_cache()

    return db.table("recipes").select(
        "*, recipe_ingredients(*, ingredients(name,unit))"
    ).eq("id", recipe_id).single().execute().data


# =============================================
# EXPENSE CATEGORIES
# =============================================
@router.get("/expense-categories")
def list_expense_categories(current_user: CurrentUser):
    result = db.table("expense_categories").select("*").eq("is_active", True).order("sort_order").execute()
    return result.data


@router.post("/expense-categories", status_code=201)
def create_expense_category(body: ExpenseCategoryCreate, current_user: SuperUser):
    result = db.table("expense_categories").insert(body.model_dump()).execute()
    return result.data[0]


# =============================================
# AUDIT LOGS
# =============================================
@router.get("/audit-logs")
def list_audit_logs(
    current_user: SuperUser,
    table_name: str = None,
    limit: int = 100,
    offset: int = 0
):
    q = db.table("audit_logs").select(
        "*, users(full_name, role)"
    ).order("created_at", desc=True).limit(limit).offset(offset)
    if table_name:
        q = q.eq("table_name", table_name)
    result = q.execute()
    return result.data
