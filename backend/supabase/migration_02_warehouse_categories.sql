-- =============================================
-- OMBOR KATEGORIYALARI (DEPARTMENTLAR) — FAQAT BELGILANGANLAR
-- =============================================

-- 1. Berilgan 5 ta kategoriyani qo'shish yoki yangilash
INSERT INTO departments (name, code, sort_order) VALUES
    ('Salat mahsulotlari', 'SALAD', 1),
    ('Go''sht mahsulotlari',    'MEAT',  2),
    ('Ichimliklar',     'DRINK', 3),
    ('Ko''mir',          'COAL',  4),
    ('Shashlik',        'SHASH', 5)
ON CONFLICT (code) DO UPDATE SET
    name = EXCLUDED.name,
    sort_order = EXCLUDED.sort_order,
    is_active = TRUE;

-- 2. Boshqa barcha bo'limlarni o'chirish (yoki nofaol qilish)
-- Diqqat: O'chirish ("DELETE") xavfli bo'lishi mumkin (bog'langan mahsulotlar bo'lsa)
-- Shuning uchun "is_active = FALSE" qilish tavsiya etiladi.
UPDATE departments 
SET is_active = FALSE 
WHERE code NOT IN ('SALAD', 'MEAT', 'DRINK', 'COAL', 'SHASH');
