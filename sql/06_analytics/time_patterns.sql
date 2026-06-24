-- Step 6: Advanced Analytics — Time Pattern Analysis
-- Goal: Identify peak order volumes by Day of Week and Hour of Day to optimize logistics and staffing.

DROP VIEW IF EXISTS view_time_patterns;

CREATE VIEW view_time_patterns AS
WITH pattern_raw AS (
    SELECT 
        order_id,
        total_payment,
        -- Extract day of week (0 = Sunday, 1 = Monday, ..., 6 = Saturday)
        EXTRACT(DOW FROM purchase_timestamp) as day_of_week,
        -- Extract hour of day (0 to 23)
        EXTRACT(HOUR FROM purchase_timestamp) as hour_of_day
    FROM fact_orders
    WHERE order_status NOT IN ('canceled', 'unavailable')
)
SELECT 
    day_of_week,
    -- Map numerical day to text for readable presentation
    CASE day_of_week
        WHEN 0 THEN 'Sunday'
        WHEN 1 THEN 'Monday'
        WHEN 2 THEN 'Tuesday'
        WHEN 3 THEN 'Wednesday'
        WHEN 4 THEN 'Thursday'
        WHEN 5 THEN 'Friday'
        WHEN 6 THEN 'Saturday'
    END as day_name,
    hour_of_day,
    COUNT(*) as order_count,
    ROUND(SUM(total_payment), 2) as total_revenue,
    -- Percentage of total orders
    ROUND((COUNT(*)::numeric / SUM(COUNT(*)) OVER ()) * 100, 2) as order_share_pct
FROM pattern_raw
GROUP BY day_of_week, hour_of_day;

-- Query 1: Top 5 peak hours of the day (overall)
SELECT 
    hour_of_day,
    SUM(order_count) as total_orders,
    ROUND((SUM(order_count)::numeric / SUM(SUM(order_count)) OVER ()) * 100, 2) as share_pct
FROM view_time_patterns
GROUP BY hour_of_day
ORDER BY total_orders DESC
LIMIT 5;

-- Query 2: Weekly order distribution
SELECT 
    day_name,
    SUM(order_count) as total_orders,
    ROUND((SUM(order_count)::numeric / SUM(SUM(order_count)) OVER ()) * 100, 2) as share_pct
FROM view_time_patterns
GROUP BY day_of_week, day_name
ORDER BY day_of_week;
