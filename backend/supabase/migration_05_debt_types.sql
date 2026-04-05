-- 1. Add debt_type to debts table
ALTER TABLE debts ADD COLUMN IF NOT EXISTS debt_type TEXT NOT NULL DEFAULT 'receive' CHECK (debt_type IN ('receive', 'pay'));

-- 2. Update process_inventory_receipt to use 'pay' debt type
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

    -- 5. Ledger Entry
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

    -- 6. Agar to'lanmagan bo'lsa, qarz yaratish (ENDI 'pay' turi bilan)
    IF NOT p_is_paid THEN
        INSERT INTO debts (debtor_name, initial_amount, remaining_amount, description, debt_date, created_by, debt_type)
        VALUES (p_supplier, v_total_amount, v_total_amount, 'Ombor xaridi uchun qarz', p_receipt_date, p_created_by, 'pay');
    END IF;

    UPDATE inventory_receipts SET total_amount = v_total_amount WHERE id = v_receipt_id;

    RETURN v_receipt_id;
END;
$$ LANGUAGE plpgsql;
