-- Step 5: CEO Strategic KPIs (Monthly Trends & MoM Growth)
-- Goal: Calculate monthly Revenue, Orders, AOV, and Month-over-Month growth rates.

-- 1. Create a view so the dashboard can easily query this pre-calculated trend
DROP VIEW IF EXISTS view_ceo_monthly_kpis;

CREATE VIEW view_ceo_monthly_kpis AS
WITH monthly_metrics AS (
    SELECT 
        DATE_TRUNC('month', purchase_timestamp)::date as order_month,
        COUNT(order_id) as total_orders,
        SUM(total_payment) as total_revenue,
        ROUND(SUM(total_payment) / COUNT(order_id), 2) as avg_order_value
    FROM fact_orders
    -- Exclude incomplete orders if they are canceled or unavailable (standard practice)
    WHERE order_status NOT IN ('canceled', 'unavailable')
    GROUP BY 1
),
monthly_lagged AS (
    SELECT 
        order_month,
        total_orders,
        total_revenue,
        avg_order_value,
        -- Get the previous month's revenue and orders using the LAG window function
        LAG(total_revenue, 1) OVER (ORDER BY order_month) as prev_month_revenue,
        LAG(total_orders, 1) OVER (ORDER BY order_month) as prev_month_orders
    FROM monthly_metrics
)
SELECT 
    order_month,
    total_orders,
    total_revenue,
    avg_order_value,
    -- Calculate MoM Revenue Growth Rate
    ROUND(
        ((total_revenue - prev_month_revenue) / NULLIF(prev_month_revenue, 0)) * 100, 
        2
    ) as mom_revenue_growth_pct,
    -- Calculate MoM Orders Growth Rate
    ROUND(
        ((total_orders - prev_month_orders)::numeric / NULLIF(prev_month_orders, 0)) * 100, 
        2
    ) as mom_orders_growth_pct
FROM monthly_lagged
ORDER BY order_month DESC;

-- 2. Query the view to check the latest months
SELECT * FROM view_ceo_monthly_kpis LIMIT 10;
