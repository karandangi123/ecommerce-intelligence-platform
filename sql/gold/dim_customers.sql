CREATE TABLE IF NOT EXISTS dim_customers (
    user_id INTEGER PRIMARY KEY,
    first_order_date DATE NOT NULL,
    total_orders INTEGER NOT NULL,
    total_spend DOUBLE NOT NULL,
    rfm_recency INTEGER NOT NULL,
    rfm_frequency INTEGER NOT NULL,
    rfm_monetary DOUBLE NOT NULL,
    rfm_segment VARCHAR NOT NULL,
    clv DOUBLE NOT NULL
);
