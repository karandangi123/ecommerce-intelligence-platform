-- Star Schema: Create and Populate dim_sellers
-- Goal: Model a clean seller dimension table.

DROP TABLE IF EXISTS dim_sellers CASCADE;

-- 1. Create table with constraints
CREATE TABLE dim_sellers (
    seller_id VARCHAR(50) PRIMARY KEY,
    zip_code_prefix VARCHAR(10) NOT NULL,
    city VARCHAR(100) NOT NULL,
    state CHAR(2) NOT NULL
);

-- 2. Populate table with clean casing
INSERT INTO dim_sellers (
    seller_id,
    zip_code_prefix,
    city,
    state
)
SELECT DISTINCT ON (seller_id)
    seller_id,
    seller_zip_code_prefix as zip_code_prefix,
    INITCAP(seller_city) as city,
    UPPER(seller_state) as state
FROM raw_sellers
ORDER BY seller_id;
