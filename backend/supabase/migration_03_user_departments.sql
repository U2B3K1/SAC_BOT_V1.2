-- =============================================
-- ROLLARNI KENGAYTIRISH: DEPARTMENT_ID QO'SHISH
-- =============================================

-- users jadvaliga department_id ustunini qo'shish
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS department_id UUID REFERENCES departments(id);

-- Eslatma: mavjud manager'lar uchun department_id NULL bo'lib qoladi.
-- Bu "hamma bo'limlarga ruxsat" yoki "hali biriktirilmagan" degan ma'noni anglatadi.
