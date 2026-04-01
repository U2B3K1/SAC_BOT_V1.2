-- 1. Debts jadvaliga debt_type qo'shish
ALTER TABLE debts ADD COLUMN IF NOT EXISTS debt_type TEXT DEFAULT 'receive' CHECK (debt_type IN ('receive', 'pay'));

-- 2. Eski qarzlarni 'receive' qilib belgilash (mijoz qarzi default bo'ladi)
UPDATE debts SET debt_type = 'receive' WHERE debt_type IS NULL;

-- 3. Yangi bo'limlarni kiritish yoki borini yangilash
INSERT INTO departments (name, code, sort_order) VALUES
    ('Kuxniya I',    'K1',    1),
    ('Kuxniya II',   'K2',    2),
    ('Shashlik',     'SHASH', 3),
    ('Salat',        'SAL',   4),
    ('Ichimliklar',  'DRINK', 5)
ON CONFLICT (name) DO UPDATE SET sort_order = EXCLUDED.sort_order;

-- Endi eski Kuxnya 1 degan ismlar bo'lsa uni o'chirib yoki ismini o'zgartirishingiz mumkin.
-- Shunchaki Supabase Dashboard dan "Kuxnya 1" ni nomini "Kuxniya I" ga o'zgartirish kifoya, yuqoridagi kod uni qo'shadi agar yo'q bo'lsa.
