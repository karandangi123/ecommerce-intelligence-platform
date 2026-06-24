-- Star Schema: Create and Populate fact_deliveries
-- Goal: Calculate delivery durations, estimates, and late-status at the Order-Seller grain.

DROP TABLE IF EXISTS fact_deliveries CASCADE;

-- 1. Create table with constraints
CREATE TABLE fact_deliveries (
    order_id VARCHAR(50) NOT NULL,
    seller_id VARCHAR(50) NOT NULL REFERENCES dim_sellers(seller_id),
    customer_unique_id VARCHAR(50) NOT NULL REFERENCES dim_customers(customer_unique_id),
    purchase_timestamp TIMESTAMP NOT NULL,
    delivered_customer_timestamp TIMESTAMP,
    estimated_delivery_timestamp TIMESTAMP NOT NULL,
    actual_delivery_days NUMERIC(5, 2),
    estimated_delivery_days NUMERIC(5, 2),
    days_difference NUMERIC(5, 2), -- Negative if early, positive if late (days)
    is_late INT DEFAULT 0, -- 1 if late, 0 if on time/early
    PRIMARY KEY (order_id, seller_id)
);

-- 2. Populate table and calculate intervals
-- We join orders, customers, and order items to get the granular relationships
INSERT INTO fact_deliveries (
    order_id,
    seller_id,
    customer_unique_id,
    purchase_timestamp,
    delivered_customer_timestamp,
    estimated_delivery_timestamp,
    actual_delivery_days,
    estimated_delivery_days,
    days_difference,
    is_late
)
SELECT DISTINCT ON (o.order_id, i.seller_id)
    o.order_id,
    i.seller_id,
    c.customer_unique_id,
    o.order_purchase_timestamp::timestamp as purchase_timestamp,
    NULLIF(o.order_delivered_customer_date, '')::timestamp as delivered_customer_timestamp,
    o.order_estimated_delivery_date::timestamp as estimated_delivery_timestamp,
    
    -- Actual delivery days = (delivery date - purchase date) converted to fractional days
    CASE 
        WHEN NULLIF(o.order_delivered_customer_date, '') IS NOT NULL 
        THEN EXTRACT(EPOCH FROM (o.order_delivered_customer_date::timestamp - o.order_purchase_timestamp::timestamp)) / 86400.0
        ELSE NULL
    END as actual_delivery_days,

    -- Estimated delivery days = (estimate date - purchase date)
    EXTRACT(EPOCH FROM (o.order_estimated_delivery_date::timestamp - o.order_purchase_timestamp::timestamp)) / 86400.0 as estimated_delivery_days,

    -- Days difference = (actual delivery date - estimated delivery date)
    CASE 
        WHEN NULLIF(o.order_delivered_customer_date, '') IS NOT NULL 
        THEN EXTRACT(EPOCH FROM (o.order_delivered_customer_date::timestamp - o.order_estimated_delivery_date::timestamp)) / 86400.0
        ELSE NULL
    END as days_difference,

    -- is_late = 1 if delivered date is after estimated date, or if order is still undelivered and past estimate
    CASE 
        WHEN NULLIF(o.order_delivered_customer_date, '') IS NOT NULL 
             AND o.order_delivered_customer_date::timestamp > o.order_estimated_delivery_date::timestamp THEN 1
        -- If not delivered yet and the current system date is past estimate (for historical accuracy we compare against order status 'delivered')
        ELSE 0
    END as is_late
FROM raw_orders o
INNER JOIN raw_customers c ON o.customer_id = c.customer_id
INNER JOIN raw_order_items i ON o.order_id = i.order_id
-- We only track deliveries for orders that were shipped or delivered
WHERE o.order_status IN ('delivered', 'shipped')
ORDER BY o.order_id, i.seller_id;
