-- Star Schema: Create and Populate dim_products
-- Goal: Model a clean product dimension with English category names and casted numeric specifications.

-- 1. Create table with appropriate constraints
DROP TABLE IF EXISTS dim_products CASCADE;

CREATE TABLE dim_products (
    product_id VARCHAR(50) PRIMARY KEY,
    category_english VARCHAR(100) NOT NULL,
    weight_g INT,
    length_cm INT,
    height_cm INT,
    width_cm INT
);

-- 2. Populate table with cleaned and translated data
INSERT INTO dim_products (
    product_id,
    category_english,
    weight_g,
    length_cm,
    height_cm,
    width_cm
)
SELECT 
    p.product_id,
    -- Handle missing Portuguese category or missing translation by defaulting to 'unknown'
    COALESCE(t.product_category_name_english, 'unknown') as category_english,
    -- Cast text dimensions to integers (using NULLIF to handle blank strings safely)
    NULLIF(p.product_weight_g, '')::INTEGER as weight_g,
    NULLIF(p.product_length_cm, '')::INTEGER as length_cm,
    NULLIF(p.product_height_cm, '')::INTEGER as height_cm,
    NULLIF(p.product_width_cm, '')::INTEGER as width_cm
FROM raw_products p
LEFT JOIN raw_category_translation t 
    ON p.product_category_name = t.product_category_name;
