-- =============================================
-- RESTORAN BOSHQARUV TIZIMI — Supabase SQL Schema
-- Supabase Dashboard > SQL Editor da bajaring
-- =============================================

-- UUID extension
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =============================================
-- MASTER DATA JADVALLARI (Super User boshqaradi)
-- =============================================

-- FOYDALANUVCHILAR
CREATE TABLE IF NOT EXISTS users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_id BIGINT UNIQUE NOT NULL,
    full_name   TEXT NOT NULL,
    phone       TEXT,
    role        TEXT NOT NULL DEFAULT 'manager' CHECK (role IN ('super_user', 'manager')),
    is_active   BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW(),
    created_by  UUID REFERENCES users(id)
);

-- BO'LIMLAR (DEPARTMENTLAR)
CREATE TABLE IF NOT EXISTS departments (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL UNIQUE,
    code        TEXT NOT NULL UNIQUE,
    is_active   BOOLEAN DEFAULT TRUE,
    sort_order  INT DEFAULT 0,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Default departmentlar
INSERT INTO departments (name, code, sort_order) VALUES
    ('Kuxnya 1',    'K1',    1),
    ('Kuxnya 2',    'K2',    2),
    ('Salat',       'SAL',   3),
    ('Ichimliklar', 'DRINK', 4),
    ('Shashlik',    'SHASH', 5)
ON CONFLICT DO NOTHING;

-- MAHSULOTLAR (TAOMLAR)
CREATE TABLE IF NOT EXISTS products (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    department_id   UUID REFERENCES departments(id) NOT NULL,
    name            TEXT NOT NULL,
    name_aliases    TEXT[] DEFAULT '{}',
    unit            TEXT DEFAULT 'porsiya',
    sale_price      NUMERIC(12,2) NOT NULL DEFAULT 0,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- INGREDIENTLAR (XOM ASHYO)
CREATE TABLE IF NOT EXISTS ingredients (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL UNIQUE,
    unit            TEXT NOT NULL,
    cost_per_unit   NUMERIC(12,4) NOT NULL DEFAULT 0,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- RETSEPTLAR
CREATE TABLE IF NOT EXISTS recipes (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id          UUID REFERENCES products(id) UNIQUE NOT NULL,
    yield_kg            NUMERIC(8,3),
    portions_per_kg     NUMERIC(8,2),
    notes               TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

-- RETSEPT INGREDIENTLARI
CREATE TABLE IF NOT EXISTS recipe_ingredients (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recipe_id       UUID REFERENCES recipes(id) ON DELETE CASCADE NOT NULL,
    ingredient_id   UUID REFERENCES ingredients(id) NOT NULL,
    quantity        NUMERIC(10,4) NOT NULL,
    unit            TEXT NOT NULL,
    UNIQUE(recipe_id, ingredient_id)
);

-- NARX KONFIGURATSIYALARI
CREATE TABLE IF NOT EXISTS price_configs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id  UUID REFERENCES products(id) NOT NULL,
    price       NUMERIC(12,2) NOT NULL,
    valid_from  DATE NOT NULL DEFAULT CURRENT_DATE,
    valid_to    DATE,
    notes       TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    created_by  UUID REFERENCES users(id)
);

-- XARAJAT KATEGORIYALARI
CREATE TABLE IF NOT EXISTS expense_categories (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL UNIQUE,
    code        TEXT NOT NULL UNIQUE,
    description TEXT,
    is_active   BOOLEAN DEFAULT TRUE,
    sort_order  INT DEFAULT 0
);

INSERT INTO expense_categories (name, code, sort_order) VALUES
    ('Gel (Gaz)',        'GEL',  1),
    ('Bunaga',           'BNG',  2),
    ('Osvijitel',        'OSV',  3),
    ('Ishchi haqi',      'SAL',  4),
    ('Elektr',           'ELK',  5),
    ('Boshqa xarajatlar','OTH',  6)
ON CONFLICT DO NOTHING;

-- =============================================
-- TRANSACTIONAL DATA JADVALLARI (Manager kiritadi)
-- =============================================

-- KUNLIK HISOBOTLAR
CREATE TABLE IF NOT EXISTS daily_reports (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_date     DATE NOT NULL,
    department_id   UUID REFERENCES departments(id) NOT NULL,
    status          TEXT DEFAULT 'draft' CHECK (status IN ('draft','submitted','approved')),
    total_revenue   NUMERIC(14,2) DEFAULT 0,
    total_cost      NUMERIC(14,2) DEFAULT 0,
    gross_profit    NUMERIC(14,2) DEFAULT 0,
    total_expenses  NUMERIC(14,2) DEFAULT 0,
    net_profit      NUMERIC(14,2) DEFAULT 0,
    opening_balance NUMERIC(14,2) DEFAULT 0,
    closing_balance NUMERIC(14,2) DEFAULT 0,
    notes           TEXT,
    created_by      UUID REFERENCES users(id) NOT NULL,
    submitted_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(report_date, department_id)
);

-- SOTUVLAR
CREATE TABLE IF NOT EXISTS sales (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    daily_report_id UUID REFERENCES daily_reports(id) ON DELETE CASCADE NOT NULL,
    product_id      UUID REFERENCES products(id) NOT NULL,
    quantity        NUMERIC(10,2) NOT NULL,
    unit_price      NUMERIC(12,2) NOT NULL,
    total_amount    NUMERIC(14,2) GENERATED ALWAYS AS (quantity * unit_price) STORED,
    cost_per_unit   NUMERIC(12,4) DEFAULT 0,
    total_cost      NUMERIC(14,2) DEFAULT 0,
    input_method    TEXT DEFAULT 'manual' CHECK (input_method IN ('screenshot','audio','excel','manual')),
    ai_session_id   UUID,
    notes           TEXT,
    created_by      UUID REFERENCES users(id) NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- XARAJATLAR
CREATE TABLE IF NOT EXISTS expenses (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    daily_report_id     UUID REFERENCES daily_reports(id) ON DELETE CASCADE NOT NULL,
    category_id         UUID REFERENCES expense_categories(id) NOT NULL,
    amount              NUMERIC(14,2) NOT NULL,
    description         TEXT,
    receipt_url         TEXT,
    input_method        TEXT DEFAULT 'manual' CHECK (input_method IN ('screenshot','audio','excel','manual')),
    ai_session_id       UUID,
    created_by          UUID REFERENCES users(id) NOT NULL,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- OMBOR KIRIMI
CREATE TABLE IF NOT EXISTS inventory_receipts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    receipt_date    DATE NOT NULL DEFAULT CURRENT_DATE,
    department_id   UUID REFERENCES departments(id),
    supplier        TEXT,
    total_amount    NUMERIC(14,2) DEFAULT 0,
    invoice_url     TEXT,
    notes           TEXT,
    created_by      UUID REFERENCES users(id) NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS inventory_receipt_items (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    receipt_id      UUID REFERENCES inventory_receipts(id) ON DELETE CASCADE NOT NULL,
    ingredient_id   UUID REFERENCES ingredients(id) NOT NULL,
    quantity        NUMERIC(10,3) NOT NULL,
    unit            TEXT NOT NULL,
    unit_cost       NUMERIC(12,4) NOT NULL,
    total_cost      NUMERIC(14,2) GENERATED ALWAYS AS (quantity * unit_cost) STORED
);

-- OMBOR REAL QOLDIG'I
CREATE TABLE IF NOT EXISTS inventory_stock (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ingredient_id   UUID REFERENCES ingredients(id) UNIQUE NOT NULL,
    quantity        NUMERIC(10,3) NOT NULL DEFAULT 0,
    last_counted_at TIMESTAMPTZ,
    last_updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- OMBOR TUZATMALARI
CREATE TABLE IF NOT EXISTS inventory_adjustments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ingredient_id   UUID REFERENCES ingredients(id) NOT NULL,
    adj_date        DATE NOT NULL DEFAULT CURRENT_DATE,
    theoretical_qty NUMERIC(10,3),
    actual_qty      NUMERIC(10,3),
    difference      NUMERIC(10,3) GENERATED ALWAYS AS (actual_qty - theoretical_qty) STORED,
    reason          TEXT,
    created_by      UUID REFERENCES users(id) NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- QARZLAR (CRM)
CREATE TABLE IF NOT EXISTS debts (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    debtor_name         TEXT NOT NULL,
    organization        TEXT,
    phone               TEXT,
    initial_amount      NUMERIC(14,2) NOT NULL,
    remaining_amount    NUMERIC(14,2) NOT NULL,
    description         TEXT,
    debt_date           DATE NOT NULL DEFAULT CURRENT_DATE,
    due_date            DATE,
    status              TEXT DEFAULT 'active' CHECK (status IN ('active','partially_paid','paid')),
    sms_sent_count      INT DEFAULT 0,
    notes               TEXT,
    created_by          UUID REFERENCES users(id) NOT NULL,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

-- QARZ TO'LOVLARI
CREATE TABLE IF NOT EXISTS debt_payments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    debt_id         UUID REFERENCES debts(id) ON DELETE CASCADE NOT NULL,
    amount          NUMERIC(14,2) NOT NULL,
    payment_date    DATE NOT NULL DEFAULT CURRENT_DATE,
    notes           TEXT,
    created_by      UUID REFERENCES users(id) NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- AI PARSING SESSIYALARI
CREATE TABLE IF NOT EXISTS ai_parse_sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_type    TEXT CHECK (session_type IN ('screenshot','audio','excel')),
    file_url        TEXT,
    raw_ai_output   JSONB,
    parsed_data     JSONB,
    status          TEXT DEFAULT 'pending' CHECK (status IN ('pending','confirmed','rejected','partial')),
    error_message   TEXT,
    confirmed_by    UUID REFERENCES users(id),
    confirmed_at    TIMESTAMPTZ,
    created_by      UUID REFERENCES users(id) NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- AUDIT LOG
CREATE TABLE IF NOT EXISTS audit_logs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES users(id),
    table_name  TEXT NOT NULL,
    record_id   UUID,
    action      TEXT NOT NULL CHECK (action IN ('INSERT','UPDATE','DELETE')),
    old_data    JSONB,
    new_data    JSONB,
    ip_address  TEXT,
    user_agent  TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================
-- INDEKSLAR
-- =============================================
CREATE INDEX IF NOT EXISTS idx_sales_report ON sales(daily_report_id);
CREATE INDEX IF NOT EXISTS idx_sales_product ON sales(product_id);
CREATE INDEX IF NOT EXISTS idx_expenses_report ON expenses(daily_report_id);
CREATE INDEX IF NOT EXISTS idx_debts_status ON debts(status);
CREATE INDEX IF NOT EXISTS idx_debts_phone ON debts(phone);
CREATE INDEX IF NOT EXISTS idx_audit_user_time ON audit_logs(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_daily_reports_date ON daily_reports(report_date DESC);
CREATE INDEX IF NOT EXISTS idx_daily_reports_dept ON daily_reports(department_id, report_date DESC);
CREATE INDEX IF NOT EXISTS idx_inventory_stock_ingredient ON inventory_stock(ingredient_id);

-- =============================================
-- TRIGGERLAR
-- =============================================

-- updated_at trigger funksiyasi
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trigger_products_updated_at
    BEFORE UPDATE ON products
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trigger_daily_reports_updated_at
    BEFORE UPDATE ON daily_reports
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trigger_debts_updated_at
    BEFORE UPDATE ON debts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Qarz to'lovi keyin remaining_amount avtomatik yangilansin
CREATE OR REPLACE FUNCTION update_debt_remaining()
RETURNS TRIGGER AS $$
DECLARE
    total_paid NUMERIC;
BEGIN
    SELECT COALESCE(SUM(amount), 0) INTO total_paid
    FROM debt_payments WHERE debt_id = NEW.debt_id;

    UPDATE debts SET
        remaining_amount = GREATEST(0, initial_amount - total_paid),
        status = CASE
            WHEN total_paid >= initial_amount THEN 'paid'
            WHEN total_paid > 0 THEN 'partially_paid'
            ELSE 'active'
        END,
        updated_at = NOW()
    WHERE id = NEW.debt_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_debt_payment_update
    AFTER INSERT ON debt_payments
    FOR EACH ROW EXECUTE FUNCTION update_debt_remaining();

-- Sotuv kiritilganda daily_report totallari yangilansin
CREATE OR REPLACE FUNCTION update_report_totals()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE daily_reports SET
        total_revenue = (SELECT COALESCE(SUM(total_amount),0) FROM sales WHERE daily_report_id = COALESCE(NEW.daily_report_id, OLD.daily_report_id)),
        total_cost    = (SELECT COALESCE(SUM(total_cost),0) FROM sales WHERE daily_report_id = COALESCE(NEW.daily_report_id, OLD.daily_report_id)),
        gross_profit  = total_revenue - total_cost,
        total_expenses= (SELECT COALESCE(SUM(amount),0) FROM expenses WHERE daily_report_id = COALESCE(NEW.daily_report_id, OLD.daily_report_id)),
        net_profit    = gross_profit - total_expenses,
        closing_balance = opening_balance + total_revenue - total_expenses - total_cost,
        updated_at    = NOW()
    WHERE id = COALESCE(NEW.daily_report_id, OLD.daily_report_id);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_sales_update_report
    AFTER INSERT OR UPDATE OR DELETE ON sales
    FOR EACH ROW EXECUTE FUNCTION update_report_totals();

CREATE TRIGGER trigger_expenses_update_report
    AFTER INSERT OR UPDATE OR DELETE ON expenses
    FOR EACH ROW EXECUTE FUNCTION update_report_totals();

-- Ombor kirimi stock'ni yangilasin
CREATE OR REPLACE FUNCTION update_stock_on_receipt()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO inventory_stock (ingredient_id, quantity)
    VALUES (NEW.ingredient_id, NEW.quantity)
    ON CONFLICT (ingredient_id)
    DO UPDATE SET
        quantity = inventory_stock.quantity + NEW.quantity,
        last_updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_receipt_update_stock
    AFTER INSERT ON inventory_receipt_items
    FOR EACH ROW EXECUTE FUNCTION update_stock_on_receipt();

-- =============================================
-- ROW LEVEL SECURITY (RLS)
-- =============================================

-- Barcha jadvallarda RLS yoqish
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE departments ENABLE ROW LEVEL SECURITY;
ALTER TABLE products ENABLE ROW LEVEL SECURITY;
ALTER TABLE ingredients ENABLE ROW LEVEL SECURITY;
ALTER TABLE recipes ENABLE ROW LEVEL SECURITY;
ALTER TABLE recipe_ingredients ENABLE ROW LEVEL SECURITY;
ALTER TABLE price_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE expense_categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE sales ENABLE ROW LEVEL SECURITY;
ALTER TABLE expenses ENABLE ROW LEVEL SECURITY;
ALTER TABLE inventory_receipts ENABLE ROW LEVEL SECURITY;
ALTER TABLE inventory_receipt_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE inventory_stock ENABLE ROW LEVEL SECURITY;
ALTER TABLE inventory_adjustments ENABLE ROW LEVEL SECURITY;
ALTER TABLE debts ENABLE ROW LEVEL SECURITY;
ALTER TABLE debt_payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_parse_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

-- Yordamchi funksiya: joriy foydalanuvchi roli
CREATE OR REPLACE FUNCTION current_user_role()
RETURNS TEXT AS $$
    SELECT role FROM users WHERE telegram_id = (
        SELECT (current_setting('app.telegram_id', true))::BIGINT
    );
$$ LANGUAGE sql STABLE;

CREATE OR REPLACE FUNCTION is_super_user()
RETURNS BOOLEAN AS $$
    SELECT current_user_role() = 'super_user';
$$ LANGUAGE sql STABLE;

-- Service role hamma narsani ko'rsin (backend uchun)
-- Manager faqat o'z ma'lumotlarini ko'rsin
CREATE POLICY "all_access_service_role" ON daily_reports
    FOR ALL USING (true); -- Backend service_role key bilan ishlaydi

-- Qolgan jadvallar uchun ham xuddi shunday (backend service_role orqali)
CREATE POLICY "all_access_sr" ON sales FOR ALL USING (true);
CREATE POLICY "all_access_sr" ON expenses FOR ALL USING (true);
CREATE POLICY "all_access_sr" ON debts FOR ALL USING (true);
CREATE POLICY "all_access_sr" ON debt_payments FOR ALL USING (true);
CREATE POLICY "all_access_sr" ON inventory_receipts FOR ALL USING (true);
CREATE POLICY "all_access_sr" ON inventory_receipt_items FOR ALL USING (true);
CREATE POLICY "all_access_sr" ON inventory_stock FOR ALL USING (true);
CREATE POLICY "all_access_sr" ON inventory_adjustments FOR ALL USING (true);
CREATE POLICY "all_access_sr" ON ai_parse_sessions FOR ALL USING (true);
CREATE POLICY "all_access_sr" ON audit_logs FOR ALL USING (true);
CREATE POLICY "all_access_sr" ON users FOR ALL USING (true);
CREATE POLICY "all_access_sr" ON departments FOR ALL USING (true);
CREATE POLICY "all_access_sr" ON products FOR ALL USING (true);
CREATE POLICY "all_access_sr" ON ingredients FOR ALL USING (true);
CREATE POLICY "all_access_sr" ON recipes FOR ALL USING (true);
CREATE POLICY "all_access_sr" ON recipe_ingredients FOR ALL USING (true);
CREATE POLICY "all_access_sr" ON price_configs FOR ALL USING (true);
CREATE POLICY "all_access_sr" ON expense_categories FOR ALL USING (true);
