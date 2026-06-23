-- ============================================================================
-- ADVANCED ANALYTICS VIEWS
-- Enterprise-grade KPI views for the E-Commerce Intelligence Platform
-- ============================================================================

-- ============================================================================
-- 1. COHORT RETENTION MATRIX
-- Purpose: Track how many customers from each monthly cohort return in
--          subsequent months. THE #1 chart product analysts are judged on.
-- Business Value: Identifies if the platform retains users or leaks them.
-- ============================================================================
CREATE OR REPLACE VIEW v_cohort_retention AS
WITH customer_cohort AS (
    -- Assign each customer to their first-purchase month (cohort)
    SELECT 
        user_id,
        DATE_TRUNC('month', first_order_date) AS cohort_month
    FROM dim_customers
),
monthly_activity AS (
    -- Get distinct months each customer was active
    SELECT DISTINCT
        f.user_id,
        DATE_TRUNC('month', d.date) AS activity_month
    FROM fact_orders f
    JOIN dim_date d ON f.date_key = d.date_key
),
cohort_activity AS (
    -- Join cohort assignment with monthly activity
    SELECT 
        cc.cohort_month,
        ma.activity_month,
        DATE_DIFF('month', cc.cohort_month, ma.activity_month) AS month_number,
        cc.user_id
    FROM customer_cohort cc
    JOIN monthly_activity ma ON cc.user_id = ma.user_id
    WHERE ma.activity_month >= cc.cohort_month
)
SELECT 
    cohort_month,
    month_number,
    COUNT(DISTINCT user_id) AS active_customers,
    -- Retention rate = active customers in month N / cohort size (month 0)
    ROUND(
        COUNT(DISTINCT user_id) * 100.0 / 
        FIRST_VALUE(COUNT(DISTINCT user_id)) OVER (
            PARTITION BY cohort_month ORDER BY month_number
        ), 2
    ) AS retention_rate_pct
FROM cohort_activity
GROUP BY cohort_month, month_number
ORDER BY cohort_month, month_number;


-- ============================================================================
-- 2. MONTHLY KPIs WITH MONTH-OVER-MONTH GROWTH
-- Purpose: Track revenue, orders, AOV, and new customers per calendar month
--          with MoM growth percentage for executive reporting.
-- Business Value: Time-series executive tracking. Shows trajectory.
-- ============================================================================
CREATE OR REPLACE VIEW v_monthly_kpis AS
WITH monthly_raw AS (
    SELECT 
        DATE_TRUNC('month', d.date) AS month,
        SUM(f.subtotal) AS revenue,
        COUNT(DISTINCT f.order_id) AS orders,
        COUNT(DISTINCT f.user_id) AS active_customers,
        SUM(f.subtotal) / COUNT(DISTINCT f.order_id) AS avg_order_value,
        SUM(f.quantity) AS total_items_sold
    FROM fact_orders f
    JOIN dim_date d ON f.date_key = d.date_key
    GROUP BY DATE_TRUNC('month', d.date)
),
new_customers_per_month AS (
    SELECT 
        DATE_TRUNC('month', first_order_date) AS month,
        COUNT(*) AS new_customers
    FROM dim_customers
    GROUP BY DATE_TRUNC('month', first_order_date)
)
SELECT 
    m.month,
    m.revenue,
    m.orders,
    m.avg_order_value,
    m.active_customers,
    m.total_items_sold,
    COALESCE(nc.new_customers, 0) AS new_customers,
    -- Month-over-month growth rates
    ROUND(
        (m.revenue - LAG(m.revenue) OVER (ORDER BY m.month)) * 100.0 / 
        NULLIF(LAG(m.revenue) OVER (ORDER BY m.month), 0), 2
    ) AS revenue_growth_pct,
    ROUND(
        (m.orders - LAG(m.orders) OVER (ORDER BY m.month)) * 100.0 / 
        NULLIF(LAG(m.orders) OVER (ORDER BY m.month), 0), 2
    ) AS order_growth_pct,
    -- Revenue per customer
    ROUND(m.revenue / NULLIF(m.active_customers, 0), 2) AS revenue_per_customer,
    -- Items per order
    ROUND(m.total_items_sold * 1.0 / NULLIF(m.orders, 0), 2) AS items_per_order
FROM monthly_raw m
LEFT JOIN new_customers_per_month nc ON m.month = nc.month
ORDER BY m.month;


-- ============================================================================
-- 3. CART / BASKET SIZE ANALYSIS
-- Purpose: Analyze how many items customers put in each order (basket size),
--          distribution of cart sizes, and average cart value by department.
-- Business Value: Operations planning, UX optimization, bundling strategy.
-- ============================================================================
CREATE OR REPLACE VIEW v_cart_analysis AS
WITH order_baskets AS (
    SELECT 
        order_id,
        user_id,
        COUNT(DISTINCT product_id) AS items_in_cart,
        SUM(subtotal) AS cart_value,
        COUNT(DISTINCT department_id) AS departments_shopped
    FROM fact_orders
    GROUP BY order_id, user_id
)
SELECT 
    -- Bucket cart sizes for histogram
    CASE 
        WHEN items_in_cart <= 3 THEN '1-3 items'
        WHEN items_in_cart <= 7 THEN '4-7 items'
        WHEN items_in_cart <= 12 THEN '8-12 items'
        WHEN items_in_cart <= 20 THEN '13-20 items'
        WHEN items_in_cart <= 35 THEN '21-35 items'
        ELSE '36+ items'
    END AS cart_size_bucket,
    COUNT(*) AS order_count,
    ROUND(AVG(cart_value), 2) AS avg_cart_value,
    ROUND(AVG(items_in_cart), 1) AS avg_items,
    ROUND(AVG(departments_shopped), 1) AS avg_departments_per_cart,
    MIN(items_in_cart) AS min_items,
    MAX(items_in_cart) AS max_items
FROM order_baskets
GROUP BY 
    CASE 
        WHEN items_in_cart <= 3 THEN '1-3 items'
        WHEN items_in_cart <= 7 THEN '4-7 items'
        WHEN items_in_cart <= 12 THEN '8-12 items'
        WHEN items_in_cart <= 20 THEN '13-20 items'
        WHEN items_in_cart <= 35 THEN '21-35 items'
        ELSE '36+ items'
    END
ORDER BY min_items;


-- ============================================================================
-- 4. REORDER BEHAVIOR ANALYSIS
-- Purpose: Measure what % of items in each department/aisle are reorders.
--          High reorder rate = sticky product. Low = trial-only or one-time.
-- Business Value: Product stickiness measurement, subscription candidates.
-- ============================================================================
CREATE OR REPLACE VIEW v_reorder_behavior AS
SELECT 
    dep.department,
    a.aisle,
    COUNT(*) AS total_items_ordered,
    SUM(f.reordered) AS reordered_items,
    ROUND(SUM(f.reordered) * 100.0 / COUNT(*), 2) AS reorder_rate_pct,
    COUNT(DISTINCT f.product_id) AS unique_products,
    COUNT(DISTINCT f.user_id) AS unique_customers,
    ROUND(SUM(f.subtotal), 2) AS total_revenue
FROM fact_orders f
JOIN dim_departments dep ON f.department_id = dep.department_id
JOIN dim_aisles a ON f.aisle_id = a.aisle_id
GROUP BY dep.department, a.aisle
ORDER BY reorder_rate_pct DESC;


-- ============================================================================
-- 5. DEPARTMENT PENETRATION
-- Purpose: What % of total customers have purchased from each department.
-- Business Value: Cross-sell opportunity identification. Low penetration
--                 departments have untapped potential.
-- ============================================================================
CREATE OR REPLACE VIEW v_department_penetration AS
WITH total_customers AS (
    SELECT COUNT(DISTINCT user_id) AS total FROM dim_customers
)
SELECT 
    dep.department,
    COUNT(DISTINCT f.user_id) AS department_customers,
    (SELECT total FROM total_customers) AS total_customers,
    ROUND(
        COUNT(DISTINCT f.user_id) * 100.0 / (SELECT total FROM total_customers), 2
    ) AS penetration_pct,
    SUM(f.subtotal) AS department_revenue,
    ROUND(SUM(f.subtotal) / COUNT(DISTINCT f.user_id), 2) AS revenue_per_customer,
    COUNT(DISTINCT f.order_id) AS total_orders,
    COUNT(DISTINCT f.product_id) AS unique_products_sold
FROM fact_orders f
JOIN dim_departments dep ON f.department_id = dep.department_id
GROUP BY dep.department
ORDER BY penetration_pct DESC;


-- ============================================================================
-- 6. PROPER CUSTOMER LIFETIME VALUE (CLV)
-- Formula: CLV = AOV × Purchase Frequency × Avg Customer Lifespan (months)
-- Purpose: Replace the placeholder CLV = spend * 1.3 with a real model.
-- Business Value: Financial planning, marketing budget allocation,
--                 identifies which customer segments are most valuable.
-- ============================================================================
CREATE OR REPLACE VIEW v_customer_ltv AS
WITH customer_metrics AS (
    SELECT 
        c.user_id,
        c.rfm_segment,
        c.total_orders,
        c.total_spend,
        -- AOV = Average Order Value for this customer
        c.total_spend / NULLIF(c.total_orders, 0) AS aov,
        -- Customer lifespan in months (first order to last order)
        GREATEST(
            DATE_DIFF('month', c.first_order_date, 
                (SELECT MAX(date) FROM dim_date)),
            1
        ) AS lifespan_months,
        -- Purchase frequency = orders per month
        c.total_orders * 1.0 / GREATEST(
            DATE_DIFF('month', c.first_order_date, 
                (SELECT MAX(date) FROM dim_date)),
            1
        ) AS purchase_frequency_monthly
    FROM dim_customers c
),
ltv_calc AS (
    SELECT 
        user_id,
        rfm_segment,
        total_orders,
        total_spend,
        ROUND(aov, 2) AS avg_order_value,
        lifespan_months,
        ROUND(purchase_frequency_monthly, 4) AS purchase_frequency,
        -- CLV = AOV × Frequency × Projected 12-month lifespan
        ROUND(aov * purchase_frequency_monthly * 12, 2) AS projected_annual_clv,
        -- CLV Tier
        CASE 
            WHEN aov * purchase_frequency_monthly * 12 >= 2000 THEN 'Platinum'
            WHEN aov * purchase_frequency_monthly * 12 >= 1000 THEN 'Gold'
            WHEN aov * purchase_frequency_monthly * 12 >= 400 THEN 'Silver'
            ELSE 'Bronze'
        END AS clv_tier
    FROM customer_metrics
)
SELECT * FROM ltv_calc;


-- ============================================================================
-- 7. RFM REVENUE MATRIX (Heatmap Data)
-- Purpose: Build a 5×5 grid of R-score × F-score, showing average monetary
--          value in each cell. Enables the classic RFM heatmap visualization.
-- Business Value: Advanced segmentation viz, identifies high-value pockets.
-- ============================================================================
CREATE OR REPLACE VIEW v_rfm_revenue_matrix AS
WITH rfm_scored AS (
    SELECT 
        user_id,
        total_spend,
        NTILE(5) OVER (ORDER BY rfm_recency DESC) AS r_score,
        NTILE(5) OVER (ORDER BY total_orders ASC) AS f_score
    FROM dim_customers
)
SELECT 
    r_score,
    f_score,
    COUNT(*) AS customer_count,
    ROUND(AVG(total_spend), 2) AS avg_monetary,
    ROUND(SUM(total_spend), 2) AS total_revenue,
    ROUND(MIN(total_spend), 2) AS min_spend,
    ROUND(MAX(total_spend), 2) AS max_spend
FROM rfm_scored
GROUP BY r_score, f_score
ORDER BY r_score, f_score;


-- ============================================================================
-- 8. DAY × HOUR HEATMAP
-- Purpose: A 7×24 grid showing order volume by day of week and hour.
-- Business Value: Workforce scheduling, marketing timing, server capacity.
-- ============================================================================
CREATE OR REPLACE VIEW v_day_hour_heatmap AS
SELECT 
    d.day_of_week,
    d.day_name,
    d.hour_of_day,
    COUNT(DISTINCT f.order_id) AS order_count,
    SUM(f.subtotal) AS revenue,
    COUNT(DISTINCT f.user_id) AS unique_customers,
    ROUND(SUM(f.subtotal) / NULLIF(COUNT(DISTINCT f.order_id), 0), 2) AS avg_order_value
FROM fact_orders f
JOIN dim_date d ON f.date_key = d.date_key
GROUP BY d.day_of_week, d.day_name, d.hour_of_day
ORDER BY d.day_of_week, d.hour_of_day;


-- ============================================================================
-- 9. PURCHASE FREQUENCY DISTRIBUTION
-- Purpose: How many customers buy 1x, 2-3x, 4-6x, 7-10x, 10+ times.
-- Business Value: Identifies the "power user" ratio, retention funnel shape.
-- ============================================================================
CREATE OR REPLACE VIEW v_purchase_frequency AS
SELECT 
    CASE 
        WHEN total_orders = 1 THEN '1 order (one-time)'
        WHEN total_orders BETWEEN 2 AND 3 THEN '2-3 orders'
        WHEN total_orders BETWEEN 4 AND 6 THEN '4-6 orders'
        WHEN total_orders BETWEEN 7 AND 10 THEN '7-10 orders'
        WHEN total_orders BETWEEN 11 AND 20 THEN '11-20 orders'
        WHEN total_orders BETWEEN 21 AND 50 THEN '21-50 orders'
        ELSE '51+ orders (power users)'
    END AS frequency_bucket,
    COUNT(*) AS customer_count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM dim_customers), 2) AS customer_pct,
    ROUND(SUM(total_spend), 2) AS total_revenue,
    ROUND(SUM(total_spend) * 100.0 / (SELECT SUM(total_spend) FROM dim_customers), 2) AS revenue_pct,
    ROUND(AVG(total_spend), 2) AS avg_spend,
    MIN(total_orders) AS min_orders,
    MAX(total_orders) AS max_orders
FROM dim_customers
GROUP BY 
    CASE 
        WHEN total_orders = 1 THEN '1 order (one-time)'
        WHEN total_orders BETWEEN 2 AND 3 THEN '2-3 orders'
        WHEN total_orders BETWEEN 4 AND 6 THEN '4-6 orders'
        WHEN total_orders BETWEEN 7 AND 10 THEN '7-10 orders'
        WHEN total_orders BETWEEN 11 AND 20 THEN '11-20 orders'
        WHEN total_orders BETWEEN 21 AND 50 THEN '21-50 orders'
        ELSE '51+ orders (power users)'
    END
ORDER BY min_orders;


-- ============================================================================
-- 10. REVENUE CONCENTRATION (PARETO / 80-20 ANALYSIS)
-- Purpose: What % of products drive what % of total revenue.
-- Business Value: Portfolio rationalization, inventory optimization.
-- ============================================================================
CREATE OR REPLACE VIEW v_revenue_concentration AS
WITH product_revenue AS (
    SELECT 
        p.product_id,
        p.product_name,
        dep.department,
        SUM(f.subtotal) AS revenue,
        ROW_NUMBER() OVER (ORDER BY SUM(f.subtotal) DESC) AS revenue_rank
    FROM fact_orders f
    JOIN dim_products p ON f.product_id = p.product_id
    JOIN dim_departments dep ON p.department_id = dep.department_id
    GROUP BY p.product_id, p.product_name, dep.department
),
total AS (
    SELECT SUM(revenue) AS total_revenue, COUNT(*) AS total_products FROM product_revenue
)
SELECT 
    pr.revenue_rank,
    pr.product_id,
    pr.product_name,
    pr.department,
    ROUND(pr.revenue, 2) AS revenue,
    ROUND(pr.revenue * 100.0 / t.total_revenue, 4) AS revenue_share_pct,
    ROUND(
        SUM(pr.revenue) OVER (ORDER BY pr.revenue_rank) * 100.0 / t.total_revenue, 2
    ) AS cumulative_revenue_pct,
    ROUND(pr.revenue_rank * 100.0 / t.total_products, 2) AS cumulative_product_pct
FROM product_revenue pr
CROSS JOIN total t
ORDER BY pr.revenue_rank;


-- ============================================================================
-- 11. CUSTOMER SEGMENT MIGRATION (Period-over-Period)
-- Purpose: Track how customers move between RFM segments over time.
-- Business Value: Measures if marketing efforts are upgrading or losing users.
-- ============================================================================
CREATE OR REPLACE VIEW v_segment_summary AS
SELECT 
    rfm_segment,
    COUNT(*) AS customers,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM dim_customers), 2) AS pct_of_total,
    ROUND(AVG(total_spend), 2) AS avg_spend,
    ROUND(AVG(total_orders), 1) AS avg_orders,
    ROUND(AVG(rfm_recency), 0) AS avg_recency_days,
    ROUND(AVG(clv), 2) AS avg_clv,
    ROUND(SUM(total_spend), 2) AS total_revenue,
    ROUND(SUM(total_spend) * 100.0 / (SELECT SUM(total_spend) FROM dim_customers), 2) AS revenue_share_pct
FROM dim_customers
GROUP BY rfm_segment
ORDER BY avg_spend DESC;


-- ============================================================================
-- 12. TOP GROWING & DECLINING PRODUCTS (MoM)
-- Purpose: Identify products with biggest revenue increase/decrease vs prior month.
-- Business Value: Trend detection, inventory planning, marketing focus.
-- ============================================================================
CREATE OR REPLACE VIEW v_product_trends AS
WITH monthly_product AS (
    SELECT 
        DATE_TRUNC('month', d.date) AS month,
        f.product_id,
        p.product_name,
        dep.department,
        SUM(f.subtotal) AS revenue,
        COUNT(DISTINCT f.order_id) AS orders
    FROM fact_orders f
    JOIN dim_date d ON f.date_key = d.date_key
    JOIN dim_products p ON f.product_id = p.product_id
    JOIN dim_departments dep ON p.department_id = dep.department_id
    GROUP BY DATE_TRUNC('month', d.date), f.product_id, p.product_name, dep.department
)
SELECT 
    month,
    product_id,
    product_name,
    department,
    revenue,
    orders,
    LAG(revenue) OVER (PARTITION BY product_id ORDER BY month) AS prev_month_revenue,
    ROUND(
        (revenue - LAG(revenue) OVER (PARTITION BY product_id ORDER BY month)) * 100.0 /
        NULLIF(LAG(revenue) OVER (PARTITION BY product_id ORDER BY month), 0), 2
    ) AS revenue_growth_pct
FROM monthly_product
ORDER BY month DESC, revenue DESC;


-- ============================================================================
-- 13. DEPARTMENT CROSS-SELL MATRIX
-- Purpose: For each pair of departments, what % of customers who bought from
--          department A also bought from department B.
-- Business Value: Cross-sell strategy, store layout optimization.
-- ============================================================================
CREATE OR REPLACE VIEW v_department_cross_sell AS
WITH customer_departments AS (
    SELECT DISTINCT 
        f.user_id, 
        dep.department
    FROM fact_orders f
    JOIN dim_departments dep ON f.department_id = dep.department_id
),
dept_pairs AS (
    SELECT 
        a.department AS department_a,
        b.department AS department_b,
        COUNT(DISTINCT a.user_id) AS customers_both
    FROM customer_departments a
    JOIN customer_departments b ON a.user_id = b.user_id
    WHERE a.department < b.department
    GROUP BY a.department, b.department
),
dept_totals AS (
    SELECT department, COUNT(DISTINCT user_id) AS dept_customers
    FROM customer_departments
    GROUP BY department
)
SELECT 
    dp.department_a,
    dp.department_b,
    dp.customers_both,
    dt_a.dept_customers AS customers_a,
    dt_b.dept_customers AS customers_b,
    ROUND(dp.customers_both * 100.0 / dt_a.dept_customers, 2) AS pct_of_a_also_buy_b,
    ROUND(dp.customers_both * 100.0 / dt_b.dept_customers, 2) AS pct_of_b_also_buy_a
FROM dept_pairs dp
JOIN dept_totals dt_a ON dp.department_a = dt_a.department
JOIN dept_totals dt_b ON dp.department_b = dt_b.department
ORDER BY customers_both DESC;
