-- Step 6: Advanced Analytics — RFM Customer Segmentation
-- Goal: Calculate Recency, Frequency, and Monetary values, score them, and segment customers.

DROP VIEW IF EXISTS view_rfm_segmentation;

CREATE VIEW view_rfm_segmentation AS
WITH customer_rfm_raw AS (
    -- 1. Calculate raw RFM metrics relative to the latest purchase in the dataset
    SELECT 
        customer_unique_id,
        -- Reference date is the max purchase timestamp in the dataset
        (SELECT MAX(purchase_timestamp) FROM fact_orders) as ref_date,
        -- Recency: Days between customer's last purchase and the reference date
        EXTRACT(DAY FROM ((SELECT MAX(purchase_timestamp) FROM fact_orders) - MAX(purchase_timestamp))) as raw_recency_days,
        -- Frequency: Count of unique orders
        COUNT(order_id) as raw_frequency,
        -- Monetary: Total spend
        SUM(total_payment) as raw_monetary
    FROM fact_orders
    WHERE order_status NOT IN ('canceled', 'unavailable')
    GROUP BY customer_unique_id
),
rfm_scores AS (
    -- 2. Rank and Score Recency, Frequency, and Monetary
    SELECT 
        customer_unique_id,
        raw_recency_days,
        raw_frequency,
        raw_monetary,
        -- Recency: Lower days = Higher Score (1 to 4)
        NTILE(4) OVER (ORDER BY raw_recency_days DESC) as r_score,
        -- Frequency: Custom rules due to extreme concentration of 1-time buyers
        CASE 
            WHEN raw_frequency = 1 THEN 1
            WHEN raw_frequency = 2 THEN 3
            ELSE 4
        END as f_score,
        -- Monetary: Higher spend = Higher Score (1 to 4)
        NTILE(4) OVER (ORDER BY raw_monetary ASC) as m_score
    FROM customer_rfm_raw
)
-- 3. Categorize into strategic business segments
SELECT 
    customer_unique_id,
    raw_recency_days,
    raw_frequency,
    raw_monetary,
    r_score,
    f_score,
    m_score,
    CASE 
        WHEN r_score = 4 AND f_score >= 3 AND m_score >= 3 THEN 'Champions'
        WHEN r_score >= 3 AND f_score >= 3 THEN 'Loyal'
        WHEN r_score >= 3 AND f_score = 1 THEN 'New / Recent'
        WHEN r_score <= 2 AND f_score >= 3 THEN 'At Risk / Can''t Lose'
        WHEN r_score = 1 AND f_score = 1 AND m_score = 1 THEN 'Lost'
        ELSE 'About to Sleep / Cold'
    END as rfm_segment
FROM rfm_scores;

-- Query the segment distribution and revenue contribution to validate
SELECT 
    rfm_segment,
    COUNT(*) as customer_count,
    ROUND((COUNT(*)::numeric / SUM(COUNT(*)) OVER ()) * 100, 2) as customer_share_pct,
    ROUND(SUM(raw_monetary), 2) as total_revenue,
    ROUND((SUM(raw_monetary) / SUM(SUM(raw_monetary)) OVER ()) * 100, 2) as revenue_share_pct,
    ROUND(AVG(raw_monetary), 2) as aov
FROM view_rfm_segmentation
GROUP BY rfm_segment
ORDER BY total_revenue DESC;
