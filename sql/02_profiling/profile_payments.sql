-- Data Profiling for raw_order_payments
-- Goal: Analyze payment types, identify negative/zero transaction amounts.

-- 1. Distribution of Payment Types
SELECT 
    payment_type,
    COUNT(*) as transaction_count,
    ROUND(SUM(payment_value::numeric), 2) as total_payment_value
FROM raw_order_payments
GROUP BY payment_type
ORDER BY transaction_count DESC;

-- 2. Value Metrics & Anomalies (values <= 0)
SELECT 
    MIN(payment_value::numeric) as min_payment,
    MAX(payment_value::numeric) as max_payment,
    ROUND(AVG(payment_value::numeric), 2) as avg_payment,
    COUNT(*) FILTER (WHERE payment_value::numeric <= 0) as zero_or_negative_count
FROM raw_order_payments;
