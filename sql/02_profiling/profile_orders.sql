-- Data Profiling for raw_orders table
-- Goal: Understand row counts, missing values (NULLs/blanks), and duplicate keys.

-- 1. Total Row Count
SELECT 
    'total_rows' as metric, 
    COUNT(*) as val 
FROM raw_orders

UNION ALL

-- 2. Check for Duplicate order_ids (Should be 0 if order_id is a unique key)
SELECT 
    'duplicate_order_ids' as metric, 
    COUNT(*) as val
FROM (
    SELECT order_id 
    FROM raw_orders 
    GROUP BY order_id 
    HAVING COUNT(*) > 1
) dupes;

-- 3. Check for NULL or Empty values across key columns
SELECT 
    COUNT(*) as total_records,
    COUNT(*) FILTER (WHERE order_id IS NULL OR order_id = '') as missing_order_id,
    COUNT(*) FILTER (WHERE customer_id IS NULL OR customer_id = '') as missing_customer_id,
    COUNT(*) FILTER (WHERE order_status IS NULL OR order_status = '') as missing_order_status,
    COUNT(*) FILTER (WHERE order_purchase_timestamp IS NULL OR order_purchase_timestamp = '') as missing_purchase_timestamp,
    COUNT(*) FILTER (WHERE order_delivered_customer_date IS NULL OR order_delivered_customer_date = '') as missing_delivered_date
FROM raw_orders;
