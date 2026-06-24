-- Data Profiling for raw_products and translations
-- Goal: Identify missing categories and un-translated Portuguese categories.

-- 1. Total products and missing category count
SELECT 
    COUNT(*) as total_products,
    COUNT(*) FILTER (WHERE product_category_name IS NULL OR product_category_name = '') as missing_category_name
FROM raw_products;

-- 2. Find unique categories in raw_products that are NOT in the translation table
SELECT DISTINCT 
    p.product_category_name as untranslated_category
FROM raw_products p
LEFT JOIN raw_category_translation t 
    ON p.product_category_name = t.product_category_name
WHERE 
    p.product_category_name IS NOT NULL 
    AND p.product_category_name <> ''
    AND t.product_category_name IS NULL;
