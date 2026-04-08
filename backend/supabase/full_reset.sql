-- ============================================================
-- SAC_BOT v1.2 — TO'LIQ DATABASE RESET & SETUP
-- Supabase Dashboard → SQL Editor → Run
-- ⚠️  DIQQAT: Bu skript mavjud barcha jadval va ma'lumotlarni O'CHIRADI
-- ============================================================


-- ============================================================
-- 0. TOZALASH — Hamma narsani o'chirish (teskari tartibda)
-- ============================================================
DROP TABLE IF EXISTS audit_logs               CASCADE;
DROP TABLE IF EXISTS ai_parse_sessions        CASCADE;
DROP TABLE IF EXISTS pending_actions          CASCADE;
DROP TABLE IF EXISTS ledger_entries           CASCADE;
DROP TABLE IF EXISTS inventory_batches        CASCADE;
DROP TABLE IF EXISTS inventory_adjustments    CASCADE;
DROP TABLE IF EXISTS inventory_stock          CASCADE;
DROP TABLE IF EXISTS inventory_receipt_items  CASCADE;
DROP TABLE IF EXISTS inventory_receipts       CASCADE;
DROP TABLE IF EXISTS debt_payments            CASCADE;
DROP TABLE IF EXISTS debts                    CASCADE;
DROP TABLE IF EXISTS expenses                 CASCADE;
DROP TABLE IF EXISTS sales                    CASCADE;
DROP TABLE IF EXISTS daily_reports            CASCADE;
DROP TABLE IF EXISTS price_configs            CASCADE;
DROP TABLE IF EXISTS recipe_ingredients       CASCADE;
DROP TABLE IF EXISTS recipes                  CASCADE;
DROP TABLE IF EXISTS products                 CASCADE;
DROP TABLE IF EXISTS expense_categories       CASCADE;
DROP TABLE IF EXISTS ingredients              CASCADE;
DROP TABLE IF EXISTS users                    CASCADE;
DROP TABLE IF EXISTS departments              CASCADE;

-- Funksiyalarni o'chirish
DROP FUNCTION IF EXISTS update_updated_at()        CASCADE;
DROP FUNCTION IF EXISTS update_debt_remaining()    CASCADE;
DROP FUNCTION IF EXISTS update_report_totals()     CASCADE;
DROP FUNCTION IF EXISTS update_stock_on_receipt()  CASCADE;
DROP FUNCTION IF EXISTS process_inventory_receipt  CASCADE;
DROP FUNCTION IF EXISTS process_sale_fifo          CASCADE;
DROP FUNCTION IF EXISTS current_user_role()        CASCADE;
DROP FUNCTION IF EXISTS is_super_user()            CASCADE;

-- Extension
CREATE EXTENSION IF NOT EXISTS "pgcrypto";


-- ============================================================
-- 1. MASTER DATA JADVALLARI
-- ============================================================

-- BO'LIMLAR (DEPARTMENTLAR) — users dan oldin yaratilishi shart
CREATE TABLE departments (
    id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name       TEXT        NOT NULL UNIQUE,
    code       TEXT        NOT NULL UNIQUE,
    is_active  BOOLEAN     DEFAULT TRUE,
    sort_order INT         DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- FOYDALANUVCHILAR
CREATE TABLE users (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_id   BIGINT      UNIQUE NOT NULL,
    full_name     TEXT        NOT NULL,
    phone         TEXT,
    role          TEXT        NOT NULL DEFAULT 'manager'
                              CHECK (role IN ('super_user', 'manager')),
    department_id UUID        REFERENCES departments(id),
    is_active     BOOLEAN     DEFAULT TRUE,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW(),
    created_by    UUID        REFERENCES users(id)
);

-- MAHSULOTLAR (TAOMLAR)
CREATE TABLE products (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    department_id UUID        NOT NULL REFERENCES departments(id),
    name          TEXT        NOT NULL,
    name_aliases  TEXT[]      DEFAULT '{}',
    unit          TEXT        DEFAULT 'porsiya',
    sale_price    NUMERIC(12,2) NOT NULL DEFAULT 0,
    is_active     BOOLEAN     DEFAULT TRUE,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW()
);

-- INGREDIENTLAR (XOM ASHYO)
CREATE TABLE ingredients (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name          TEXT        NOT NULL UNIQUE,
    unit          TEXT        NOT NULL,
    cost_per_unit NUMERIC(12,4) NOT NULL DEFAULT 0,
    is_active     BOOLEAN     DEFAULT TRUE,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW()
);

-- RETSEPTLAR
CREATE TABLE recipes (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id      UUID        NOT NULL UNIQUE REFERENCES products(id),
    yield_kg        NUMERIC(8,3),
    portions_per_kg NUMERIC(8,2),
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- RETSEPT INGREDIENTLARI
CREATE TABLE recipe_ingredients (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    recipe_id     UUID        NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    ingredient_id UUID        NOT NULL REFERENCES ingredients(id),
    quantity      NUMERIC(10,4) NOT NULL,
    unit          TEXT        NOT NULL,
    UNIQUE (recipe_id, ingredient_id)
);

-- XARAJAT KATEGORIYALARI
CREATE TABLE expense_categories (
    id          UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT    NOT NULL UNIQUE,
    code        TEXT    NOT NULL UNIQUE,
    description TEXT,
    is_active   BOOLEAN DEFAULT TRUE,
    sort_order  INT     DEFAULT 0
);

-- NARX KONFIGURATSIYALARI
CREATE TABLE price_configs (
    id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID        NOT NULL REFERENCES products(id),
    price      NUMERIC(12,2) NOT NULL,
    valid_from DATE        NOT NULL DEFAULT CURRENT_DATE,
    valid_to   DATE,
    notes      TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID        REFERENCES users(id)
);


-- ============================================================
-- 2. TRANSAKSIONAL JADVALLAR
-- ============================================================

-- KUNLIK HISOBOTLAR
CREATE TABLE daily_reports (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    report_date     DATE        NOT NULL,
    department_id   UUID        NOT NULL REFERENCES departments(id),
    status          TEXT        DEFAULT 'draft'
                                CHECK (status IN ('draft','submitted','approved')),
    total_revenue   NUMERIC(14,2) DEFAULT 0,
    total_cost      NUMERIC(14,2) DEFAULT 0,
    gross_profit    NUMERIC(14,2) DEFAULT 0,
    total_expenses  NUMERIC(14,2) DEFAULT 0,
    net_profit      NUMERIC(14,2) DEFAULT 0,
    opening_balance NUMERIC(14,2) DEFAULT 0,
    closing_balance NUMERIC(14,2) DEFAULT 0,
    notes           TEXT,
    created_by      UUID        NOT NULL REFERENCES users(id),
    submitted_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (report_date, department_id)
);

-- SOTUVLAR
CREATE TABLE sales (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    daily_report_id UUID        NOT NULL REFERENCES daily_reports(id) ON DELETE CASCADE,
    product_id      UUID        NOT NULL REFERENCES products(id),
    quantity        NUMERIC(10,2) NOT NULL,
    unit_price      NUMERIC(12,2) NOT NULL,
    total_amount    NUMERIC(14,2) GENERATED ALWAYS AS (quantity * unit_price) STORED,
    cost_per_unit   NUMERIC(12,4) DEFAULT 0,
    total_cost      NUMERIC(14,2) DEFAULT 0,
    input_method    TEXT        DEFAULT 'manual'
                                CHECK (input_method IN ('screenshot','audio','excel','manual')),
    ai_session_id   UUID,
    notes           TEXT,
    created_by      UUID        NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- XARAJATLAR
CREATE TABLE expenses (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    daily_report_id UUID        NOT NULL REFERENCES daily_reports(id) ON DELETE CASCADE,
    category_id     UUID        NOT NULL REFERENCES expense_categories(id),
    amount          NUMERIC(14,2) NOT NULL,
    description     TEXT,
    receipt_url     TEXT,
    input_method    TEXT        DEFAULT 'manual'
                                CHECK (input_method IN ('screenshot','audio','excel','manual')),
    ai_session_id   UUID,
    created_by      UUID        NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- OMBOR KIRIMI (HEADER)
CREATE TABLE inventory_receipts (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    receipt_date DATE        NOT NULL DEFAULT CURRENT_DATE,
    department_id UUID       REFERENCES departments(id),
    supplier     TEXT,
    total_amount NUMERIC(14,2) DEFAULT 0,
    invoice_url  TEXT,
    notes        TEXT,
    created_by   UUID        NOT NULL REFERENCES users(id),
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

-- OMBOR KIRIMI SATRLARI
CREATE TABLE inventory_receipt_items (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    receipt_id    UUID        NOT NULL REFERENCES inventory_receipts(id) ON DELETE CASCADE,
    ingredient_id UUID        NOT NULL REFERENCES ingredients(id),
    quantity      NUMERIC(10,3) NOT NULL,
    unit          TEXT        NOT NULL,
    unit_cost     NUMERIC(12,4) NOT NULL,
    total_cost    NUMERIC(14,2) GENERATED ALWAYS AS (quantity * unit_cost) STORED
);

-- OMBOR REAL QOLDIĞI
CREATE TABLE inventory_stock (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    ingredient_id   UUID        NOT NULL UNIQUE REFERENCES ingredients(id),
    quantity        NUMERIC(10,3) NOT NULL DEFAULT 0,
    last_counted_at TIMESTAMPTZ,
    last_updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- OMBOR TUZATMALARI (Inventory Adjustment)
CREATE TABLE inventory_adjustments (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    ingredient_id   UUID        NOT NULL REFERENCES ingredients(id),
    adj_date        DATE        NOT NULL DEFAULT CURRENT_DATE,
    theoretical_qty NUMERIC(10,3),
    actual_qty      NUMERIC(10,3),
    difference      NUMERIC(10,3) GENERATED ALWAYS AS (actual_qty - theoretical_qty) STORED,
    reason          TEXT,
    created_by      UUID        NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- QARZLAR (debt_type: 'receive'=bizga qarzdor, 'pay'=biz qarzdormiz)
CREATE TABLE debts (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    debtor_name      TEXT        NOT NULL,
    organization     TEXT,
    phone            TEXT,
    debt_type        TEXT        NOT NULL DEFAULT 'receive'
                                 CHECK (debt_type IN ('receive', 'pay')),
    initial_amount   NUMERIC(14,2) NOT NULL,
    remaining_amount NUMERIC(14,2) NOT NULL,
    description      TEXT,
    debt_date        DATE        NOT NULL DEFAULT CURRENT_DATE,
    due_date         DATE,
    status           TEXT        DEFAULT 'active'
                                 CHECK (status IN ('active','partially_paid','paid')),
    sms_sent_count   INT         DEFAULT 0,
    notes            TEXT,
    created_by       UUID        NOT NULL REFERENCES users(id),
    created_at       TIMESTAMPTZ DEFAULT NOW(),
    updated_at       TIMESTAMPTZ DEFAULT NOW()
);

-- QARZ TO'LOVLARI
CREATE TABLE debt_payments (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    debt_id      UUID        NOT NULL REFERENCES debts(id) ON DELETE CASCADE,
    amount       NUMERIC(14,2) NOT NULL,
    payment_date DATE        NOT NULL DEFAULT CURRENT_DATE,
    notes        TEXT,
    created_by   UUID        NOT NULL REFERENCES users(id),
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

-- AI PARSING SESSIYALARI
CREATE TABLE ai_parse_sessions (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    session_type  TEXT        CHECK (session_type IN ('screenshot','audio','excel')),
    file_url      TEXT,
    raw_ai_output JSONB,
    parsed_data   JSONB,
    status        TEXT        DEFAULT 'pending'
                              CHECK (status IN ('pending','confirmed','rejected','partial')),
    error_message TEXT,
    confirmed_by  UUID        REFERENCES users(id),
    confirmed_at  TIMESTAMPTZ,
    created_by    UUID        NOT NULL REFERENCES users(id),
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- AUDIT LOG
CREATE TABLE audit_logs (
    id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID        REFERENCES users(id),
    table_name TEXT        NOT NULL,
    record_id  UUID,
    action     TEXT        NOT NULL CHECK (action IN ('INSERT','UPDATE','DELETE')),
    old_data   JSONB,
    new_data   JSONB,
    ip_address TEXT,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);


-- ============================================================
-- 3. FIFO & BUXGALTERIYA JADVALLARI (migration_04)
-- ============================================================

-- BUXGALTERIYA DAFTARI (Double-Entry Ledger)
CREATE TABLE ledger_entries (
    id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    entry_date     TIMESTAMPTZ DEFAULT NOW(),
    description    TEXT,
    debit_account  TEXT        NOT NULL,
    credit_account TEXT        NOT NULL,
    amount         NUMERIC(14,2) NOT NULL,
    reference_id   UUID,
    reference_type TEXT,
    department_id  UUID        REFERENCES departments(id),
    created_at     TIMESTAMPTZ DEFAULT NOW()
);

-- FIFO PARTIYALAR (Inventory Batches)
CREATE TABLE inventory_batches (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    ingredient_id UUID        NOT NULL REFERENCES ingredients(id),
    batch_date    TIMESTAMPTZ DEFAULT NOW(),
    initial_qty   NUMERIC(10,3) NOT NULL,
    remaining_qty NUMERIC(10,3) NOT NULL,
    unit_cost     NUMERIC(12,4) NOT NULL,
    department_id UUID        REFERENCES departments(id),
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- AI PENDING ACTIONS (Tasdiqlash kutayotgan harakatlar)
CREATE TABLE pending_actions (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    action_type  TEXT        NOT NULL
                             CHECK (action_type IN ('sale','receipt','expense','adjustment')),
    payload      JSONB       NOT NULL,
    status       TEXT        DEFAULT 'pending'
                             CHECK (status IN ('pending','approved','rejected')),
    notes        TEXT,
    created_by   UUID        REFERENCES users(id),
    confirmed_by UUID        REFERENCES users(id),
    confirmed_at TIMESTAMPTZ,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);


-- ============================================================
-- 4. INDEKSLAR
-- ============================================================
CREATE INDEX idx_sales_report        ON sales(daily_report_id);
CREATE INDEX idx_sales_product       ON sales(product_id);
CREATE INDEX idx_expenses_report     ON expenses(daily_report_id);
CREATE INDEX idx_debts_status        ON debts(status);
CREATE INDEX idx_debts_phone         ON debts(phone);
CREATE INDEX idx_audit_user_time     ON audit_logs(user_id, created_at DESC);
CREATE INDEX idx_daily_reports_date  ON daily_reports(report_date DESC);
CREATE INDEX idx_daily_reports_dept  ON daily_reports(department_id, report_date DESC);
CREATE INDEX idx_stock_ingredient    ON inventory_stock(ingredient_id);
CREATE INDEX idx_ledger_ref          ON ledger_entries(reference_id);
CREATE INDEX idx_batches_fifo        ON inventory_batches(ingredient_id, batch_date ASC)
                                     WHERE remaining_qty > 0;


-- ============================================================
-- 5. TRIGGERLAR
-- ============================================================

-- 5.1 updated_at trigger funksiyasi
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_products_updated_at
    BEFORE UPDATE ON products
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_daily_reports_updated_at
    BEFORE UPDATE ON daily_reports
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_debts_updated_at
    BEFORE UPDATE ON debts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- 5.2 Qarz to'lovidan keyin remaining_amount avtomatik yangilansin
CREATE OR REPLACE FUNCTION update_debt_remaining()
RETURNS TRIGGER AS $$
DECLARE total_paid NUMERIC;
BEGIN
    SELECT COALESCE(SUM(amount), 0) INTO total_paid
    FROM debt_payments WHERE debt_id = NEW.debt_id;

    UPDATE debts SET
        remaining_amount = GREATEST(0, initial_amount - total_paid),
        status = CASE
            WHEN total_paid >= initial_amount THEN 'paid'
            WHEN total_paid > 0              THEN 'partially_paid'
            ELSE 'active'
        END,
        updated_at = NOW()
    WHERE id = NEW.debt_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_debt_payment_update
    AFTER INSERT ON debt_payments
    FOR EACH ROW EXECUTE FUNCTION update_debt_remaining();

-- 5.3 Sotuv/xarajat o'zgarganda kunlik hisobot totallari yangilansin
CREATE OR REPLACE FUNCTION update_report_totals()
RETURNS TRIGGER AS $$
DECLARE rid UUID;
BEGIN
    rid := COALESCE(
        CASE TG_OP WHEN 'DELETE' THEN OLD.daily_report_id ELSE NEW.daily_report_id END,
        OLD.daily_report_id
    );

    UPDATE daily_reports SET
        total_revenue  = (SELECT COALESCE(SUM(total_amount), 0) FROM sales    WHERE daily_report_id = rid),
        total_cost     = (SELECT COALESCE(SUM(total_cost),   0) FROM sales    WHERE daily_report_id = rid),
        total_expenses = (SELECT COALESCE(SUM(amount),       0) FROM expenses WHERE daily_report_id = rid),
        gross_profit   = total_revenue - total_cost,
        net_profit     = gross_profit  - total_expenses,
        closing_balance= opening_balance + total_revenue - total_expenses - total_cost,
        updated_at     = NOW()
    WHERE id = rid;
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_sales_update_report
    AFTER INSERT OR UPDATE OR DELETE ON sales
    FOR EACH ROW EXECUTE FUNCTION update_report_totals();

CREATE TRIGGER trg_expenses_update_report
    AFTER INSERT OR UPDATE OR DELETE ON expenses
    FOR EACH ROW EXECUTE FUNCTION update_report_totals();

-- 5.4 Ombor kirimi items qo'shilganda stock avtomatik yangilansin
CREATE OR REPLACE FUNCTION update_stock_on_receipt()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO inventory_stock (ingredient_id, quantity)
    VALUES (NEW.ingredient_id, NEW.quantity)
    ON CONFLICT (ingredient_id) DO UPDATE SET
        quantity        = inventory_stock.quantity + NEW.quantity,
        last_updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_receipt_update_stock
    AFTER INSERT ON inventory_receipt_items
    FOR EACH ROW EXECUTE FUNCTION update_stock_on_receipt();


-- ============================================================
-- 6. RPC FUNKSIYALAR (Atomik tranzaksiyalar)
-- ============================================================

-- 6.1 OMBOR KIRIMI: Stock + FIFO Batch + Ledger + Qarz (bir tranzaksiyada)
CREATE OR REPLACE FUNCTION process_inventory_receipt(
    p_receipt_date  DATE,
    p_department_id UUID,
    p_supplier      TEXT,
    p_items         JSONB,
    p_is_paid       BOOLEAN,
    p_created_by    UUID
)
RETURNS UUID AS $$
DECLARE
    v_receipt_id   UUID;
    v_item         RECORD;
    v_total_amount NUMERIC := 0;
BEGIN
    INSERT INTO inventory_receipts (receipt_date, department_id, supplier, created_by)
    VALUES (p_receipt_date, p_department_id, p_supplier, p_created_by)
    RETURNING id INTO v_receipt_id;

    FOR v_item IN
        SELECT * FROM jsonb_to_recordset(p_items)
        AS x(ingredient_id UUID, quantity NUMERIC, unit_cost NUMERIC, unit TEXT)
    LOOP
        -- Satr
        INSERT INTO inventory_receipt_items (receipt_id, ingredient_id, quantity, unit, unit_cost)
        VALUES (v_receipt_id, v_item.ingredient_id, v_item.quantity, v_item.unit, v_item.unit_cost);

        -- FIFO batch
        INSERT INTO inventory_batches (ingredient_id, initial_qty, remaining_qty, unit_cost, department_id)
        VALUES (v_item.ingredient_id, v_item.quantity, v_item.quantity, v_item.unit_cost, p_department_id);

        -- Stock (trigger ham qiladi, lekin xavsizlik uchun qo'shamiz)
        INSERT INTO inventory_stock (ingredient_id, quantity)
        VALUES (v_item.ingredient_id, v_item.quantity)
        ON CONFLICT (ingredient_id)
        DO UPDATE SET quantity = inventory_stock.quantity + v_item.quantity;

        v_total_amount := v_total_amount + (v_item.quantity * v_item.unit_cost);
    END LOOP;

    -- Ledger: Debit Inventory / Credit Cash yoki AP
    INSERT INTO ledger_entries (description, debit_account, credit_account, amount, reference_id, reference_type, department_id)
    VALUES (
        'Ombor kirimi: ' || p_supplier,
        'inventory',
        CASE WHEN p_is_paid THEN 'cash' ELSE 'accounts_payable' END,
        v_total_amount,
        v_receipt_id,
        'receipt',
        p_department_id
    );

    -- Qarz (to'lanmagan bo'lsa)
    IF NOT p_is_paid THEN
        INSERT INTO debts (debtor_name, initial_amount, remaining_amount, description, debt_date, created_by, debt_type)
        VALUES (p_supplier, v_total_amount, v_total_amount, 'Ombor xaridi uchun qarz', p_receipt_date, p_created_by, 'pay');
    END IF;

    UPDATE inventory_receipts SET total_amount = v_total_amount WHERE id = v_receipt_id;
    RETURN v_receipt_id;
END;
$$ LANGUAGE plpgsql;


-- 6.2 SOTUV: FIFO COGS + Ledger + Sale record (bir tranzaksiyada)
CREATE OR REPLACE FUNCTION process_sale_fifo(
    p_daily_report_id UUID,
    p_product_id      UUID,
    p_quantity        NUMERIC,
    p_unit_price      NUMERIC,
    p_created_by      UUID
)
RETURNS UUID AS $$
DECLARE
    v_sale_id      UUID;
    v_recipe_id    UUID;
    v_ing          RECORD;
    v_batch        RECORD;
    v_needed_qty   NUMERIC;
    v_consumed_qty NUMERIC;
    v_total_cogs   NUMERIC := 0;
    v_ing_cost     NUMERIC;
    v_dept_id      UUID;
BEGIN
    SELECT department_id INTO v_dept_id FROM products WHERE id = p_product_id;
    SELECT id INTO v_recipe_id FROM recipes WHERE product_id = p_product_id;

    IF v_recipe_id IS NOT NULL THEN
        FOR v_ing IN
            SELECT ingredient_id, quantity FROM recipe_ingredients WHERE recipe_id = v_recipe_id
        LOOP
            v_needed_qty := v_ing.quantity * p_quantity;
            v_ing_cost   := 0;

            FOR v_batch IN
                SELECT id, remaining_qty, unit_cost
                FROM inventory_batches
                WHERE ingredient_id = v_ing.ingredient_id AND remaining_qty > 0
                ORDER BY batch_date ASC
            LOOP
                EXIT WHEN v_needed_qty <= 0;
                v_consumed_qty := LEAST(v_needed_qty, v_batch.remaining_qty);
                UPDATE inventory_batches SET remaining_qty = remaining_qty - v_consumed_qty WHERE id = v_batch.id;
                v_ing_cost   := v_ing_cost + (v_consumed_qty * v_batch.unit_cost);
                v_needed_qty := v_needed_qty - v_consumed_qty;
            END LOOP;

            UPDATE inventory_stock
            SET quantity = quantity - (v_ing.quantity * p_quantity)
            WHERE ingredient_id = v_ing.ingredient_id;

            v_total_cogs := v_total_cogs + v_ing_cost;
        END LOOP;
    END IF;

    INSERT INTO sales (daily_report_id, product_id, quantity, unit_price, cost_per_unit, total_cost, created_by)
    VALUES (
        p_daily_report_id, p_product_id, p_quantity, p_unit_price,
        CASE WHEN p_quantity > 0 THEN v_total_cogs / p_quantity ELSE 0 END,
        v_total_cogs,
        p_created_by
    )
    RETURNING id INTO v_sale_id;

    -- Ledger: Tushum (Debit: Cash / Credit: Sales Revenue)
    INSERT INTO ledger_entries (description, debit_account, credit_account, amount, reference_id, reference_type, department_id)
    VALUES ('Sotuv tushumi', 'cash', 'sales_revenue', p_quantity * p_unit_price, v_sale_id, 'sale', v_dept_id);

    -- Ledger: Tannarx / COGS (Debit: COGS / Credit: Inventory)
    IF v_total_cogs > 0 THEN
        INSERT INTO ledger_entries (description, debit_account, credit_account, amount, reference_id, reference_type, department_id)
        VALUES ('Sotuv tannarxi (COGS)', 'cogs', 'inventory', v_total_cogs, v_sale_id, 'sale', v_dept_id);
    END IF;

    RETURN v_sale_id;
END;
$$ LANGUAGE plpgsql;


-- ============================================================
-- 7. ROW LEVEL SECURITY (RLS)
-- Backend service_role key bilan to'g'ridan-to'g'ri ishlaydi
-- ============================================================
ALTER TABLE users                  ENABLE ROW LEVEL SECURITY;
ALTER TABLE departments            ENABLE ROW LEVEL SECURITY;
ALTER TABLE products               ENABLE ROW LEVEL SECURITY;
ALTER TABLE ingredients            ENABLE ROW LEVEL SECURITY;
ALTER TABLE recipes                ENABLE ROW LEVEL SECURITY;
ALTER TABLE recipe_ingredients     ENABLE ROW LEVEL SECURITY;
ALTER TABLE price_configs          ENABLE ROW LEVEL SECURITY;
ALTER TABLE expense_categories     ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_reports          ENABLE ROW LEVEL SECURITY;
ALTER TABLE sales                  ENABLE ROW LEVEL SECURITY;
ALTER TABLE expenses               ENABLE ROW LEVEL SECURITY;
ALTER TABLE inventory_receipts     ENABLE ROW LEVEL SECURITY;
ALTER TABLE inventory_receipt_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE inventory_stock        ENABLE ROW LEVEL SECURITY;
ALTER TABLE inventory_adjustments  ENABLE ROW LEVEL SECURITY;
ALTER TABLE debts                  ENABLE ROW LEVEL SECURITY;
ALTER TABLE debt_payments          ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_parse_sessions      ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs             ENABLE ROW LEVEL SECURITY;
ALTER TABLE ledger_entries         ENABLE ROW LEVEL SECURITY;
ALTER TABLE inventory_batches      ENABLE ROW LEVEL SECURITY;
ALTER TABLE pending_actions        ENABLE ROW LEVEL SECURITY;

-- Barcha jadvallarga service_role uchun to'liq ruxsat
DO $$
DECLARE tbl TEXT;
BEGIN
    FOREACH tbl IN ARRAY ARRAY[
        'users','departments','products','ingredients','recipes','recipe_ingredients',
        'price_configs','expense_categories','daily_reports','sales','expenses',
        'inventory_receipts','inventory_receipt_items','inventory_stock',
        'inventory_adjustments','debts','debt_payments','ai_parse_sessions',
        'audit_logs','ledger_entries','inventory_batches','pending_actions'
    ]
    LOOP
        EXECUTE format(
            'CREATE POLICY "service_role_all" ON %I FOR ALL USING (true)', tbl
        );
    END LOOP;
END $$;


-- ============================================================
-- 8. BOSHLANG'ICH MA'LUMOTLAR (Seed Data)
-- ============================================================

-- Bo'limlar
INSERT INTO departments (name, code, sort_order) VALUES
    ('Salat mahsulotlari',  'SALAD', 1),
    ('Go''sht mahsulotlari', 'MEAT',  2),
    ('Ichimliklar',          'DRINK', 3),
    ('Ko''mir',              'COAL',  4),
    ('Shashlik',             'SHASH', 5)
ON CONFLICT (code) DO UPDATE SET
    name       = EXCLUDED.name,
    sort_order = EXCLUDED.sort_order,
    is_active  = TRUE;

-- Xarajat kategoriyalari
INSERT INTO expense_categories (name, code, sort_order) VALUES
    ('Gel (Gaz)',         'GEL', 1),
    ('Bunaga',            'BNG', 2),
    ('Osvijitel',         'OSV', 3),
    ('Ishchi haqi',       'SAL', 4),
    ('Elektr',            'ELK', 5),
    ('Boshqa xarajatlar', 'OTH', 6)
ON CONFLICT (code) DO UPDATE SET
    name       = EXCLUDED.name,
    sort_order = EXCLUDED.sort_order,
    is_active  = TRUE;


-- ============================================================
-- ✅ SETUP TUGADI
-- Keyingi qadam: Supabase Dashboard → Authentication → Users
-- yoki to'g'ridan-to'g'ri users jadvaliga super_user qo'shing.
-- ============================================================
