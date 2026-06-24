-- Step 5: Marketing and Customer KPIs
-- Goal: Calculate monthly average review score, new customer acquisition, and repeat order share.

DROP VIEW IF EXISTS view_marketing_monthly_kpis;

CREATE VIEW view_marketing_monthly_kpis AS
WITH customer_first_purchase AS (
    -- Find the acquisition (first purchase) date for every customer
    SELECT 
        customer_unique_id,
        MIN(purchase_timestamp) as acquisition_timestamp
    FROM fact_orders
    WHERE order_status NOT IN ('canceled', 'unavailable')
    GROUP BY customer_unique_id
),
monthly_acquisition AS (
    -- Count new customers acquired per month
    SELECT 
        DATE_TRUNC('month', acquisition_timestamp)::date as order_month,
        COUNT(customer_unique_id) as new_customers
    FROM customer_first_purchase
    GROUP BY 1
),
order_sequence AS (
    -- Sequence orders for each customer to identify repeat purchases
    SELECT 
        order_id,
        customer_unique_id,
        purchase_timestamp,
        ROW_NUMBER() OVER (PARTITION BY customer_unique_id ORDER BY purchase_timestamp) as order_num
    FROM fact_orders
    WHERE order_status NOT IN ('canceled', 'unavailable')
),
monthly_repeats AS (
    -- Count the number of repeat orders (order_num > 1) per month
    SELECT 
        DATE_TRUNC('month', purchase_timestamp)::date as order_month,
        COUNT(*) FILTER (WHERE order_num > 1) as repeat_orders,
        COUNT(*) as total_orders
    FROM order_sequence
    GROUP BY 1
),
monthly_reviews AS (
    -- Calculate average review score per month
    -- Join with fact_orders to get the order purchase month
    SELECT 
        DATE_TRUNC('month', o.purchase_timestamp)::date as order_month,
        ROUND(AVG(r.review_score::numeric), 2) as avg_review_score
    FROM raw_order_reviews r
    INNER JOIN fact_orders o ON r.order_id = o.order_id
    GROUP BY 1
)
SELECT 
    o.order_month,
    COALESCE(a.new_customers, 0) as new_customers_acquired,
    COALESCE(r.total_orders, 0) as total_orders,
    -- Repeat order share: % of orders this month placed by return customers
    ROUND(
        (COALESCE(r.repeat_orders, 0)::numeric / NULLIF(r.total_orders, 0)) * 100, 
        2
    ) as repeat_order_share_pct,
    COALESCE(rv.avg_review_score, 0.00) as avg_review_score
FROM (SELECT DISTINCT DATE_TRUNC('month', purchase_timestamp)::date as order_month FROM fact_orders) o
LEFT JOIN monthly_acquisition a ON o.order_month = a.order_month
LEFT JOIN monthly_repeats r ON o.order_month = r.order_month
LEFT JOIN monthly_reviews rv ON o.order_month = rv.order_month
ORDER BY o.order_month DESC;

-- Query the view to check customer satisfaction and retention trends
SELECT * FROM view_marketing_monthly_kpis LIMIT 10;
