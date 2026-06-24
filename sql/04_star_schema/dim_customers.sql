-- Star Schema: Create and Populate dim_customers
-- Goal: Model a clean customer dimension deduplicated by customer_unique_id.

DROP TABLE IF EXISTS dim_customers CASCADE;

-- 1. Create table with constraints
CREATE TABLE dim_customers (
    customer_unique_id VARCHAR(50) PRIMARY KEY,
    zip_code_prefix VARCHAR(10) NOT NULL,
    city VARCHAR(100) NOT NULL,
    state CHAR(2) NOT NULL
);

-- 2. Populate table using DISTINCT ON to deduplicate
-- If a customer has multiple address records, we keep their latest order location
INSERT INTO dim_customers (
    customer_unique_id,
    zip_code_prefix,
    city,
    state
)
SELECT DISTINCT ON (customer_unique_id)
    customer_unique_id,
    customer_zip_code_prefix as zip_code_prefix,
    INITCAP(customer_city) as city, -- Capitalize city names cleanly (e.g. "sao paulo" -> "Sao Paulo")
    UPPER(customer_state) as state
FROM raw_customers
ORDER BY customer_unique_id, customer_id DESC; -- Using customer_id DESC as a proxy for the latest record
