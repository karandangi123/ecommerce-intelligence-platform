-- 1. Executive KPIs View
CREATE OR REPLACE VIEW v_executive_kpis AS
WITH order_stats AS (
    SELECT 
        order_id,
        user_id,
        sum(subtotal) AS order_total
    FROM fact_orders
    GROUP BY order_id, user_id
),
customer_stats AS (
    SELECT 
        count(distinct user_id) AS total_customers,
        count(case when total_orders > 1 then 1 end) AS repeat_customers
    FROM dim_customers
)
SELECT 
    sum(order_total) AS total_revenue,
    count(distinct order_id) AS total_orders,
    sum(order_total) / count(distinct order_id) AS average_order_value,
    total_customers AS active_customers,
    (repeat_customers * 100.0) / total_customers AS repeat_purchase_rate
FROM order_stats
CROSS JOIN customer_stats
GROUP BY total_customers, repeat_customers;

-- 2. Customer RFM Segments Summary View
CREATE OR REPLACE VIEW v_customer_analytics AS
SELECT 
    rfm_segment,
    count(*) AS customer_count,
    (count(*) * 100.0) / (SELECT count(*) FROM dim_customers) AS customer_share_pct,
    sum(total_spend) AS segment_revenue,
    (sum(total_spend) * 100.0) / (SELECT sum(total_spend) FROM dim_customers) AS revenue_share_pct,
    avg(total_spend) AS avg_customer_spend,
    avg(total_orders) AS avg_customer_orders
FROM dim_customers
GROUP BY rfm_segment;

-- 3. Product Performance & ABC View
CREATE OR REPLACE VIEW v_product_performance AS
SELECT 
    p.product_id,
    p.product_name,
    d.department,
    a.aisle,
    p.unit_price,
    count(distinct f.order_id) AS total_orders,
    sum(f.quantity) AS total_quantity_sold,
    sum(f.subtotal) AS total_revenue,
    p.abc_class
FROM fact_orders f
JOIN dim_products p ON f.product_id = p.product_id
JOIN dim_departments d ON p.department_id = d.department_id
JOIN dim_aisles a ON p.aisle_id = a.aisle_id
GROUP BY p.product_id, p.product_name, d.department, a.aisle, p.unit_price, p.abc_class;

-- 4. Hourly and Day of Week Time Patterns View
CREATE OR REPLACE VIEW v_time_patterns AS
SELECT 
    d.day_of_week,
    d.day_name,
    d.hour_of_day,
    count(distinct f.order_id) AS total_orders,
    sum(f.subtotal) AS total_revenue,
    sum(f.subtotal) / count(distinct f.order_id) AS avg_order_value
FROM fact_orders f
JOIN dim_date d ON f.date_key = d.date_key
GROUP BY d.day_of_week, d.day_name, d.hour_of_day;
