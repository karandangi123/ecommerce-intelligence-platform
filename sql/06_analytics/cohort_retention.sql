-- Step 6: Advanced Analytics — Cohort Retention Analysis
-- Goal: Calculate customer retention over months since their first purchase month.

DROP VIEW IF EXISTS view_cohort_retention;

CREATE VIEW view_cohort_retention AS
WITH customer_first_purchase AS (
    -- 1. Identify the first purchase month (cohort) for each customer
    SELECT 
        customer_unique_id,
        DATE_TRUNC('month', MIN(purchase_timestamp))::date as cohort_month
    FROM fact_orders
    WHERE order_status NOT IN ('canceled', 'unavailable')
    GROUP BY customer_unique_id
),
customer_orders AS (
    -- 2. Map all order months for each customer
    SELECT DISTINCT
        customer_unique_id,
        DATE_TRUNC('month', purchase_timestamp)::date as order_month
    FROM fact_orders
    WHERE order_status NOT IN ('canceled', 'unavailable')
),
cohort_index_calc AS (
    -- 3. Calculate the monthly index (months elapsed since cohort month)
    SELECT 
        c.customer_unique_id,
        c.cohort_month,
        o.order_month,
        -- Calculate difference in months: (Year Diff * 12) + Month Diff
        ((EXTRACT(YEAR FROM o.order_month) - EXTRACT(YEAR FROM c.cohort_month)) * 12) + 
        (EXTRACT(MONTH FROM o.order_month) - EXTRACT(MONTH FROM c.cohort_month)) as cohort_index
    FROM customer_first_purchase c
    INNER JOIN customer_orders o ON c.customer_unique_id = o.customer_unique_id
),
cohort_sizes AS (
    -- 4. Calculate total unique customers in each cohort (Month 0 size)
    SELECT 
        cohort_month,
        COUNT(DISTINCT customer_unique_id) as cohort_size
    FROM customer_first_purchase
    GROUP BY cohort_month
),
retention_counts AS (
    -- 5. Count unique customers active in each cohort index month
    SELECT 
        cohort_month,
        cohort_index,
        COUNT(DISTINCT customer_unique_id) as active_customers
    FROM cohort_index_calc
    GROUP BY cohort_month, cohort_index
)
-- 6. Combine and calculate retention percentages
SELECT 
    r.cohort_month,
    s.cohort_size,
    r.cohort_index,
    r.active_customers,
    ROUND((r.active_customers::numeric / s.cohort_size) * 100, 2) as retention_pct
FROM retention_counts r
INNER JOIN cohort_sizes s ON r.cohort_month = s.cohort_month
ORDER BY r.cohort_month DESC, r.cohort_index ASC;

-- Query the view to check retention performance for early cohorts
SELECT * 
FROM view_cohort_retention 
WHERE cohort_month BETWEEN '2017-01-01' AND '2017-06-01'
ORDER BY cohort_month, cohort_index
LIMIT 20;
