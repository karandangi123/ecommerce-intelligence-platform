-- Star Schema: Validate Row Counts and Table Structure
-- Goal: Verify the data was loaded correctly into the clean tables.

SELECT 'dim_products' as table_name, COUNT(*) as row_count FROM dim_products
UNION ALL
SELECT 'dim_customers' as table_name, COUNT(*) as row_count FROM dim_customers
UNION ALL
SELECT 'dim_sellers' as table_name, COUNT(*) as row_count FROM dim_sellers
UNION ALL
SELECT 'fact_orders' as table_name, COUNT(*) as row_count FROM fact_orders
UNION ALL
SELECT 'fact_deliveries' as table_name, COUNT(*) as row_count FROM fact_deliveries;
