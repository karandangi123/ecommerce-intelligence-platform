-- Step 5: Operations View KPIs (Monthly Delivery Performance)
-- Goal: Calculate monthly OTD%, average delivery days, and late delivery rates.

DROP VIEW IF EXISTS view_ops_monthly_kpis;

CREATE VIEW view_ops_monthly_kpis AS
SELECT 
    DATE_TRUNC('month', purchase_timestamp)::date as order_month,
    COUNT(*) as total_shipments,
    -- Count of orders that have been successfully delivered to the customer
    COUNT(delivered_customer_timestamp) as total_delivered,
    
    -- Average delivery days for completed shipments
    ROUND(AVG(actual_delivery_days), 2) as avg_delivery_days,
    
    -- On-Time Delivery Rate (OTD%): delivered on/before estimate
    ROUND(
        (COUNT(*) FILTER (WHERE is_late = 0 AND delivered_customer_timestamp IS NOT NULL)::numeric / 
         NULLIF(COUNT(delivered_customer_timestamp), 0)) * 100, 
        2
    ) as otd_pct,
    
    -- Late Delivery Rate (LDR%): delivered after estimate
    ROUND(
        (COUNT(*) FILTER (WHERE is_late = 1)::numeric / 
         NULLIF(COUNT(delivered_customer_timestamp), 0)) * 100, 
        2
    ) as late_delivery_rate_pct
FROM fact_deliveries
GROUP BY 1
ORDER BY order_month DESC;

-- Query the view to check logistics health over the last 10 months
SELECT * FROM view_ops_monthly_kpis LIMIT 10;
