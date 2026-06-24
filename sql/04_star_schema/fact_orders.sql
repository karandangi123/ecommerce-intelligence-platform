-- Star Schema: Create and Populate fact_orders
-- Goal: Aggregate financial metrics and cast timestamps for the central fact table.

DROP TABLE IF EXISTS fact_orders CASCADE;

-- 1. Create table with constraints
CREATE TABLE fact_orders (
    order_id VARCHAR(50) PRIMARY KEY,
    customer_unique_id VARCHAR(50) NOT NULL REFERENCES dim_customers(customer_unique_id),
    order_status VARCHAR(20) NOT NULL,
    purchase_timestamp TIMESTAMP NOT NULL,
    approved_timestamp TIMESTAMP,
    delivered_carrier_timestamp TIMESTAMP,
    delivered_customer_timestamp TIMESTAMP,
    estimated_delivery_timestamp TIMESTAMP NOT NULL,
    total_price NUMERIC(10, 2) DEFAULT 0.00,
    total_freight NUMERIC(10, 2) DEFAULT 0.00,
    total_payment NUMERIC(10, 2) DEFAULT 0.00
);

-- 2. Populate table with aggregated raw records and date casting
INSERT INTO fact_orders (
    order_id,
    customer_unique_id,
    order_status,
    purchase_timestamp,
    approved_timestamp,
    delivered_carrier_timestamp,
    delivered_customer_timestamp,
    estimated_delivery_timestamp,
    total_price,
    total_freight,
    total_payment
)
WITH order_items_agg AS (
    -- Aggregate total price and freight per order
    SELECT 
        order_id,
        SUM(price::numeric) as total_price,
        SUM(freight_value::numeric) as total_freight
    FROM raw_order_items
    GROUP BY order_id
),
order_payments_agg AS (
    -- Aggregate total payments per order (accounts for multi-payment orders)
    SELECT 
        order_id,
        SUM(payment_value::numeric) as total_payment
    FROM raw_order_payments
    GROUP BY order_id
)
SELECT 
    o.order_id,
    c.customer_unique_id,
    o.order_status,
    -- Safely cast date strings to timestamp. We use NULLIF to turn empty text fields to NULL.
    o.order_purchase_timestamp::timestamp as purchase_timestamp,
    NULLIF(o.order_approved_at, '')::timestamp as approved_timestamp,
    NULLIF(o.order_delivered_carrier_date, '')::timestamp as delivered_carrier_timestamp,
    NULLIF(o.order_delivered_customer_date, '')::timestamp as delivered_customer_timestamp,
    o.order_estimated_delivery_date::timestamp as estimated_delivery_timestamp,
    COALESCE(i.total_price, 0.00) as total_price,
    COALESCE(i.total_freight, 0.00) as total_freight,
    COALESCE(p.total_payment, 0.00) as total_payment
FROM raw_orders o
-- Join with customers to map temporary customer_id to permanent customer_unique_id
INNER JOIN raw_customers c 
    ON o.customer_id = c.customer_id
LEFT JOIN order_items_agg i 
    ON o.order_id = i.order_id
LEFT JOIN order_payments_agg p 
    ON o.order_id = p.order_id;
