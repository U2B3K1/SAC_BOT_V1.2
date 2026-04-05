-- =============================================
-- MIGRATION 04: DOUBLE-ENTRY ACCOUNTING & FIFO
-- =============================================

-- 1. LEDGER ENTRIES (Buxgalteriya daftari)
CREATE TABLE IF NOT EXISTS ledger_entries (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entry_date      TIMESTAMPTZ DEFAULT NOW(),
    description     TEXT,
    debit_account   TEXT NOT NULL,  -- Masalan: 'inventory', 'cash', 'cogs', 'accounts_receivable'
    credit_account  TEXT NOT NULL, -- Masalan: 'accounts_payable', 'sales_revenue', 'inventory'
    amount          NUMERIC(14,2) NOT NULL,
    reference_id    UUID,           -- Sale, Receipt yoki Expense ID-si
    reference_type  TEXT,           -- 'sale', 'receipt', 'expense', 'adjustment'
    department_id   UUID REFERENCES departments(id),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 2. INVENTORY BATCHES (FIFO uchun partiyalar)
CREATE TABLE IF NOT EXISTS inventory_batches (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ingredient_id   UUID REFERENCES ingredients(id) NOT NULL,
    batch_date      TIMESTAMPTZ DEFAULT NOW(),
    initial_qty     NUMERIC(10,3) NOT NULL,
    remaining_qty   NUMERIC(10,3) NOT NULL,
    unit_cost       NUMERIC(12,4) NOT NULL,
    department_id   UUID REFERENCES departments(id),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 3. PENDING ACTIONS (AI parsing natijalari uchun)
CREATE TABLE IF NOT EXISTS pending_actions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    action_type     TEXT NOT NULL CHECK (action_type IN ('sale', 'receipt', 'expense', 'adjustment')),
    payload         JSONB NOT NULL,
    status          TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    notes           TEXT,
    created_by      UUID REFERENCES users(id),
    confirmed_by    UUID REFERENCES users(id),
    confirmed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 4. INDEKSLAR
CREATE INDEX IF NOT EXISTS idx_ledger_ref ON ledger_entries(reference_id);
CREATE INDEX IF NOT EXISTS idx_batches_fifo ON inventory_batches(ingredient_id, batch_date ASC) WHERE remaining_qty > 0;

-- 5. RPC: INVENTAR KIRIMINI ATOMIK QILISH (Stock + Ledger + Debt)
CREATE OR REPLACE FUNCTION process_inventory_receipt(
    p_receipt_date DATE,
    p_department_id UUID,
    p_supplier TEXT,
    p_items JSONB,
    p_is_paid BOOLEAN,
    p_created_by UUID
)
RETURNS UUID AS $$
DECLARE
    v_receipt_id UUID;
    v_item RECORD;
    v_total_amount NUMERIC := 0;
BEGIN
    -- 1. Receipt yaratish
    INSERT INTO inventory_receipts (receipt_date, department_id, supplier, created_by)
    VALUES (p_receipt_date, p_department_id, p_supplier, p_created_by)
    RETURNING id INTO v_receipt_id;

    FOR v_item IN SELECT * FROM jsonb_to_recordset(p_items) AS x(ingredient_id UUID, quantity NUMERIC, unit_cost NUMERIC, unit TEXT)
    LOOP
        -- 2. Itemlarni qo'shish
        INSERT INTO inventory_receipt_items (receipt_id, ingredient_id, quantity, unit, unit_cost)
        VALUES (v_receipt_id, v_item.ingredient_id, v_item.quantity, v_item.unit, v_item.unit_cost);

        -- 3. FIFO Batch yaratish
        INSERT INTO inventory_batches (ingredient_id, initial_qty, remaining_qty, unit_cost, department_id)
        VALUES (v_item.ingredient_id, v_item.quantity, v_item.quantity, v_item.unit_cost, p_department_id);

        -- 4. Stock yangilash
        INSERT INTO inventory_stock (ingredient_id, quantity)
        VALUES (v_item.ingredient_id, v_item.quantity)
        ON CONFLICT (ingredient_id) 
        DO UPDATE SET quantity = inventory_stock.quantity + v_item.quantity;

        v_total_amount := v_total_amount + (v_item.quantity * v_item.unit_cost);
    END LOOP;

    -- 5. Ledger Entry (Debit: Inventory, Credit: Cash yoki Accounts Payable)
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

    -- 6. Agar to'lanmagan bo'lsa, qarz yaratish
    IF NOT p_is_paid THEN
        INSERT INTO debts (debtor_name, initial_amount, remaining_amount, description, debt_date, created_by)
        VALUES (p_supplier, v_total_amount, v_total_amount, 'Ombor xaridi uchun qarz', p_receipt_date, p_created_by);
    END IF;

    UPDATE inventory_receipts SET total_amount = v_total_amount WHERE id = v_receipt_id;

    RETURN v_receipt_id;
END;
$$ LANGUAGE plpgsql;

-- 6. RPC: SOTUVNI FIFO BO'YICHA AMALGA OSHIRISH (COGS + Batches + Ledger)
CREATE OR REPLACE FUNCTION process_sale_fifo(
    p_daily_report_id UUID,
    p_product_id UUID,
    p_quantity NUMERIC,
    p_unit_price NUMERIC,
    p_created_by UUID
)
RETURNS UUID AS $$
DECLARE
    v_sale_id UUID;
    v_recipe_id UUID;
    v_ing RECORD;
    v_batch RECORD;
    v_needed_qty NUMERIC;
    v_consumed_qty NUMERIC;
    v_total_cogs NUMERIC := 0;
    v_ing_cost NUMERIC := 0;
    v_department_id UUID;
BEGIN
    -- Departmentni aniqlash
    SELECT department_id INTO v_department_id FROM products WHERE id = p_product_id;

    -- 1. Retseptni topish
    SELECT id INTO v_recipe_id FROM recipes WHERE product_id = p_product_id;
    
    -- 2. Har bir ingredient uchun FIFO hisoblash
    IF v_recipe_id IS NOT NULL THEN
        FOR v_ing IN SELECT ingredient_id, quantity FROM recipe_ingredients WHERE recipe_id = v_recipe_id
        LOOP
            v_needed_qty := v_ing.quantity * p_quantity;
            v_ing_cost := 0;

            -- Batchelarni aylanib chiqish (Eski sanadan boshlab)
            FOR v_batch IN 
                SELECT id, remaining_qty, unit_cost 
                FROM inventory_batches 
                WHERE ingredient_id = v_ing.ingredient_id AND remaining_qty > 0
                ORDER BY batch_date ASC
            LOOP
                IF v_needed_qty <= 0 THEN EXIT; END IF;

                v_consumed_qty := LEAST(v_needed_qty, v_batch.remaining_qty);
                
                -- Batchdan ayirish
                UPDATE inventory_batches 
                SET remaining_qty = remaining_qty - v_consumed_qty 
                WHERE id = v_batch.id;

                v_ing_cost := v_ing_cost + (v_consumed_qty * v_batch.unit_cost);
                v_needed_qty := v_needed_qty - v_consumed_qty;
            END LOOP;

            -- Stockni yangilash
            UPDATE inventory_stock 
            SET quantity = quantity - (v_ing.quantity * p_quantity)
            WHERE ingredient_id = v_ing.ingredient_id;

            v_total_cogs := v_total_cogs + v_ing_cost;
        END LOOP;
    END IF;

    -- 3. Sale rekordini kiritish
    INSERT INTO sales (daily_report_id, product_id, quantity, unit_price, cost_per_unit, total_cost, created_by)
    VALUES (p_daily_report_id, p_product_id, p_quantity, p_unit_price, CASE WHEN p_quantity > 0 THEN v_total_cogs / p_quantity ELSE 0 END, v_total_cogs, p_created_by)
    RETURNING id INTO v_sale_id;

    -- 4. Ledger Entries
    -- A. Tushum (Debit: Cash, Credit: Sales Revenue)
    INSERT INTO ledger_entries (description, debit_account, credit_account, amount, reference_id, reference_type, department_id)
    VALUES ('Sotuv tushumi', 'cash', 'sales_revenue', p_quantity * p_unit_price, v_sale_id, 'sale', v_department_id);

    -- B. Tannarx (Debit: COGS, Credit: Inventory)
    INSERT INTO ledger_entries (description, debit_account, credit_account, amount, reference_id, reference_type, department_id)
    VALUES ('Sotuv tannarxi (COGS)', 'cogs', 'inventory', v_total_cogs, v_sale_id, 'sale', v_department_id);

    RETURN v_sale_id;
END;
$$ LANGUAGE plpgsql;
