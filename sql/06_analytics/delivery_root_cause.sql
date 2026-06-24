-- Step 6: Advanced Analytics — Delivery Root Cause Analysis
-- Goal: Determine if late deliveries are caused by Seller Delays or Carrier Delays.

DROP VIEW IF EXISTS view_delivery_root_cause;

CREATE VIEW view_delivery_root_cause AS
WITH delivery_milestones AS (
    -- 1. Gather all milestones and calculate durations for shipped/delivered orders
    SELECT 
        d.order_id,
        d.seller_id,
        s.state as seller_state,
        c.state as customer_state,
        d.purchase_timestamp,
        d.delivered_customer_timestamp,
        d.estimated_delivery_timestamp,
        d.is_late,
        
        -- Shipping limit date (from raw items)
        i.shipping_limit_timestamp,
        -- Carrier handover date (from raw orders)
        NULLIF(o.order_delivered_carrier_date, '')::timestamp as carrier_handover_timestamp,
        
        -- Flag: Did the seller hand over to the carrier LATE AND the order arrived late?
        CASE 
            WHEN d.is_late = 1 
                 AND NULLIF(o.order_delivered_carrier_date, '') IS NOT NULL 
                 AND o.order_delivered_carrier_date::timestamp > i.shipping_limit_timestamp THEN 1
            ELSE 0
        END as is_seller_late,
        
        -- Flag: Did the carrier deliver LATE, even though the seller handed it over on time?
        CASE 
            WHEN d.is_late = 1 
                 AND (NULLIF(o.order_delivered_carrier_date, '') IS NULL 
                      OR o.order_delivered_carrier_date::timestamp <= i.shipping_limit_timestamp::timestamp) THEN 1
            ELSE 0
        END as is_carrier_late
    FROM fact_deliveries d
    INNER JOIN raw_orders o ON d.order_id = o.order_id
    INNER JOIN dim_sellers s ON d.seller_id = s.seller_id
    INNER JOIN dim_customers c ON d.customer_unique_id = c.customer_unique_id
    INNER JOIN (
        -- Get the maximum shipping limit date per order-seller group as a timestamp
        SELECT order_id, seller_id, MAX(shipping_limit_date)::timestamp as shipping_limit_timestamp
        FROM raw_order_items
        GROUP BY order_id, seller_id
    ) i ON d.order_id = i.order_id AND d.seller_id = i.seller_id
)
SELECT 
    seller_state,
    customer_state,
    COUNT(*) as total_deliveries,
    SUM(is_late) as total_late_deliveries,
    -- Late rate %
    ROUND((SUM(is_late)::numeric / COUNT(*)) * 100, 2) as late_delivery_rate_pct,
    -- Of the late deliveries, how many were the seller's fault?
    ROUND((SUM(is_seller_late)::numeric / NULLIF(SUM(is_late), 0)) * 100, 2) as seller_fault_share_pct,
    -- Of the late deliveries, how many were the carrier's fault?
    ROUND((SUM(is_carrier_late)::numeric / NULLIF(SUM(is_late), 0)) * 100, 2) as carrier_fault_share_pct
FROM delivery_milestones
GROUP BY seller_state, customer_state;

-- Query the top 10 worst seller-to-customer state routes (with at least 100 shipments)
SELECT * 
FROM view_delivery_root_cause
WHERE total_deliveries >= 100
ORDER BY late_delivery_rate_pct DESC
LIMIT 10;
