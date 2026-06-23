import os
import yaml
import datetime
import polars as pl
import duckdb
from src.utils.logger import setup_logger

logger = setup_logger("medallion_pipeline")

def load_config(config_path="configs/pipeline_config.yaml"):
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

def run_silver_layer(paths):
    logger.info("Starting Silver Layer Transformations...")
    bronze_dir = paths["bronze_dir"]
    silver_dir = paths["silver_dir"]
    os.makedirs(silver_dir, exist_ok=True)
    
    # 1. Clean Departments and Aisles (simple copies)
    logger.info("Transforming Departments and Aisles...")
    pl.read_parquet(os.path.join(bronze_dir, "departments.parquet")).write_parquet(
        os.path.join(silver_dir, "departments.parquet")
    )
    pl.read_parquet(os.path.join(bronze_dir, "aisles.parquet")).write_parquet(
        os.path.join(silver_dir, "aisles.parquet")
    )
    
    # 2. Clean Products & Synthesize Prices
    logger.info("Transforming Products and Synthesizing Prices...")
    products_df = pl.read_parquet(os.path.join(bronze_dir, "products.parquet"))
    
    # Define base price by department
    department_base_prices = {
        1: 4.5,   # frozen
        2: 2.5,   # other
        3: 3.5,   # bakery
        4: 2.0,   # produce
        5: 15.0,  # alcohol
        6: 4.0,   # international
        7: 3.0,   # beverages
        8: 8.0,   # pets
        9: 2.5,   # dry goods pasta
        10: 1.5,  # bulk
        11: 6.0,  # personal care
        12: 12.0, # meat seafood
        13: 3.5,  # pantry
        14: 3.0,  # breakfast
        15: 2.0,  # canned goods
        16: 4.0,  # dairy eggs
        17: 5.0,  # household
        18: 7.0,  # babies
        19: 2.5,  # snacks
        20: 4.0,  # deli
        21: 3.0   # missing
    }
    
    # Map base prices and add offset based on product_id
    products_df = products_df.with_columns(
        pl.col("department_id").replace_strict(department_base_prices, default=3.0).alias("base_price")
    ).with_columns(
        (pl.col("base_price") + (pl.col("product_id") % 100) * 0.05).round(2).alias("unit_price")
    ).drop("base_price")
    
    products_df.write_parquet(os.path.join(silver_dir, "products.parquet"))
    
    # 3. Clean Orders and Synthesize Real Timestamps
    logger.info("Transforming Orders and Synthesizing Timestamps...")
    orders_df = pl.read_parquet(os.path.join(bronze_dir, "orders.parquet"))
    
    # Sort by user and order number for sequential timestamp generation
    orders_df = orders_df.sort(["user_id", "order_number"])
    
    # Fill missing days since prior order for first orders with 0.0
    orders_df = orders_df.with_columns(
        pl.col("days_since_prior_order").fill_null(0.0).cast(pl.Float64).alias("days")
    )
    
    # Cumulative days per user
    orders_df = orders_df.with_columns(
        pl.col("days").cum_sum().over("user_id").alias("cum_days")
    )
    
    # Add a user-level stagger (offset) so users don't start on the exact same date
    orders_df = orders_df.with_columns(
        (pl.col("user_id") % 180).alias("user_offset_days")
    )
    orders_df = orders_df.with_columns(
        (pl.col("cum_days") + pl.col("user_offset_days")).cast(pl.Int64).alias("total_days")
    )
    
    # Construct datetime: Jan 1 2025 + total_days + hour_of_day
    base_dt = datetime.datetime(2025, 1, 1)
    orders_df = orders_df.with_columns(
        (pl.lit(base_dt) + 
         pl.col("total_days") * pl.duration(days=1) + 
         pl.col("order_hour_of_day").cast(pl.Int64) * pl.duration(hours=1)).alias("order_timestamp")
    ).drop(["days", "cum_days", "user_offset_days", "total_days"])
    
    orders_df.write_parquet(os.path.join(silver_dir, "orders.parquet"))
    
    # 4. Clean Order Products (Concatenate Prior and Train)
    logger.info("Transforming Order Products (Concatenating Prior and Train)...")
    prior_df = pl.read_parquet(os.path.join(bronze_dir, "order_products__prior.parquet"))
    train_df = pl.read_parquet(os.path.join(bronze_dir, "order_products__train.parquet"))
    
    order_products_df = pl.concat([prior_df, train_df])
    order_products_df.write_parquet(os.path.join(silver_dir, "order_products.parquet"))
    
    logger.info("Silver Layer Transformations completed successfully!")

def run_gold_layer(paths):
    logger.info("Starting Gold Layer Modeling (DuckDB)...")
    silver_dir = paths["silver_dir"]
    gold_dir = paths["gold_dir"]
    db_path = paths["gold_db_path"]
    
    os.makedirs(gold_dir, exist_ok=True)
    
    # 1. Connect to DuckDB
    logger.info(f"Connecting to DuckDB database at {db_path}...")
    conn = duckdb.connect(db_path)
    
    # 2. Execute Star Schema Table definitions
    # 2. Drop existing tables and recreate them (DROP is a metadata operation that takes under 1ms, preventing heavy TRUNCATE operations)
    logger.info("Dropping existing Gold tables (if any) and creating fresh schemas...")
    for table_name in ["fact_orders", "dim_customers", "dim_products", "dim_date", "dim_aisles", "dim_departments"]:
        conn.execute(f"DROP TABLE IF EXISTS {table_name};")
        
    for sql_file in ["dim_departments.sql", "dim_aisles.sql", "dim_products.sql", "dim_date.sql", "dim_customers.sql", "fact_orders.sql"]:
        with open(os.path.join("sql", "gold", sql_file), "r") as f:
            sql_script = f.read()
            conn.execute(sql_script)
    
    # 3. Populate dim_departments and dim_aisles
    logger.info("Populating dim_departments and dim_aisles...")
    conn.execute(f"INSERT INTO dim_departments SELECT * FROM read_parquet('{silver_dir}/departments.parquet')")
    conn.execute(f"INSERT INTO dim_aisles SELECT * FROM read_parquet('{silver_dir}/aisles.parquet')")
    
    # 4. Calculate ABC Inventory Class and Populate dim_products
    logger.info("Calculating ABC Inventory Classes and Populating dim_products...")
    
    # Load products and order products to calculate revenue contribution
    products = pl.read_parquet(os.path.join(silver_dir, "products.parquet"))
    order_products = pl.read_parquet(os.path.join(silver_dir, "order_products.parquet"))
    
    # Count frequency of each product
    product_counts = order_products.group_by("product_id").len().rename({"len": "order_count"})
    
    # Join with products to get price
    product_rev = products.join(product_counts, on="product_id", how="left").fill_null(0)
    product_rev = product_rev.with_columns(
        (pl.col("order_count") * pl.col("unit_price")).alias("revenue")
    ).sort("revenue", descending=True)
    
    # Calculate cumulative revenue share
    total_revenue = product_rev["revenue"].sum()
    product_rev = product_rev.with_columns(
        (pl.col("revenue").cum_sum() / total_revenue).alias("cum_share")
    )
    
    # Assign ABC Class: A (top 80%), B (next 15%), C (bottom 5%)
    product_rev = product_rev.with_columns(
        pl.when(pl.col("cum_share") <= 0.80).then(pl.lit("A"))
        .when(pl.col("cum_share") <= 0.95).then(pl.lit("B"))
        .otherwise(pl.lit("C"))
        .alias("abc_class")
    )
    
    # Save back to silver for import
    product_rev.select(["product_id", "product_name", "aisle_id", "department_id", "unit_price", "abc_class"]).write_parquet(
        os.path.join(silver_dir, "products_gold.parquet")
    )
    
    conn.execute(f"INSERT INTO dim_products SELECT * FROM read_parquet('{silver_dir}/products_gold.parquet')")
    
    # 5. Populate dim_date
    logger.info("Building and Populating dim_date...")
    orders_df = pl.read_parquet(os.path.join(silver_dir, "orders.parquet"))
    
    # Extract unique combinations of date and hour from order_timestamp
    date_df = orders_df.select([
        pl.col("order_timestamp").dt.date().alias("date"),
        pl.col("order_hour_of_day").alias("hour_of_day")
    ]).unique().sort(["date", "hour_of_day"])
    
    # Calculate day_of_week from date
    date_df = date_df.with_columns(
        (pl.col("date").dt.weekday() % 7).alias("day_of_week")
    )
    
    # Add other calendar fields
    day_names = {0: "Sunday", 1: "Monday", 2: "Tuesday", 3: "Wednesday", 4: "Thursday", 5: "Friday", 6: "Saturday"}
    month_names = {1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June", 
                   7: "July", 8: "August", 9: "September", 10: "October", 11: "November", 12: "December"}
    
    date_df = date_df.with_columns([
        (pl.col("date").dt.year().cast(pl.Int32) * 1000000 + 
         pl.col("date").dt.month().cast(pl.Int32) * 10000 + 
         pl.col("date").dt.day().cast(pl.Int32) * 100 + 
         pl.col("hour_of_day").cast(pl.Int32)).alias("date_key"),
        pl.col("day_of_week").replace_strict(day_names, default="Unknown").alias("day_name"),
        pl.col("day_of_week").is_in([0, 6]).alias("is_weekend"),
        pl.col("date").dt.month().alias("month"),
        pl.col("date").dt.month().replace_strict(month_names, default="Unknown").alias("month_name"),
        pl.col("date").dt.year().alias("year"),
        pl.col("date").dt.quarter().alias("quarter")
    ])
    
    # Reorder columns to match dim_date schema
    date_df.select([
        "date_key", "date", "day_of_week", "day_name", "hour_of_day", "is_weekend", "month", "month_name", "year", "quarter"
    ]).write_parquet(os.path.join(silver_dir, "dim_date.parquet"))
    
    conn.execute(f"INSERT INTO dim_date SELECT * FROM read_parquet('{silver_dir}/dim_date.parquet')")
    
    # 6. Populate fact_orders using Polars LazyFrames and Streaming Execution to prevent swapping
    logger.info("Joining order products, orders, and products using Polars Lazy Streaming...")
    
    op_lazy = pl.scan_parquet(os.path.join(silver_dir, "order_products.parquet"))
    orders_lazy = pl.scan_parquet(os.path.join(silver_dir, "orders.parquet"))
    products_lazy = pl.scan_parquet(os.path.join(silver_dir, "products_gold.parquet"))
    
    # Select only required columns from orders and products to save memory
    orders_slim = orders_lazy.select(["order_id", "user_id", "order_timestamp"])
    products_slim = products_lazy.select(["product_id", "aisle_id", "department_id", "unit_price"])
    
    # Perform inner joins
    fact_lazy = op_lazy.join(orders_slim, on="order_id", how="inner")
    fact_lazy = fact_lazy.join(products_slim, on="product_id", how="inner")
    
    # Calculate date_key and synthesized columns
    logger.info("Computing synthesized columns in Polars...")
    fact_lazy = fact_lazy.with_columns([
        (pl.col("order_timestamp").dt.year().cast(pl.Int32) * 1000000 + 
         pl.col("order_timestamp").dt.month().cast(pl.Int32) * 10000 + 
         pl.col("order_timestamp").dt.day().cast(pl.Int32) * 100 + 
         pl.col("order_timestamp").dt.hour().cast(pl.Int32)).alias("date_key"),
        pl.lit(1, dtype=pl.Int32).alias("quantity"),
        pl.col("unit_price").alias("subtotal")
    ])
    
    # Select columns in matching order
    fact_lazy = fact_lazy.select([
        "order_id", "user_id", "product_id", "aisle_id", "department_id", "date_key", 
        "add_to_cart_order", "reordered", "quantity", "unit_price", "subtotal"
    ])
    
    # Execute lazy plan in streaming mode and write directly to parquet disk
    logger.info("Executing streaming join plan directly to Parquet...")
    fact_lazy.sink_parquet(
        os.path.join(silver_dir, "fact_orders.parquet"),
        compression="snappy"
    )
    
    # Bulk insert into DuckDB
    logger.info("Bulk inserting fact table into DuckDB fact_orders...")
    conn.execute(f"INSERT INTO fact_orders SELECT * FROM read_parquet('{silver_dir}/fact_orders.parquet')")
    
    # 7. Calculate RFM + CLV and Populate dim_customers
    logger.info("Populating dim_customers with RFM Segmentation...")
    insert_customers_sql = """
    INSERT INTO dim_customers
    WITH customer_raw AS (
        SELECT 
            user_id,
            min(d.date) AS first_order_date,
            count(distinct order_id) AS total_orders,
            sum(subtotal) AS total_spend,
            max(d.date) AS last_order_date
        FROM fact_orders f
        JOIN dim_date d ON f.date_key = d.date_key
        GROUP BY user_id
    ),
    study_end AS (
        SELECT max(last_order_date) + INTERVAL 1 DAY AS end_date FROM customer_raw
    ),
    rfm_base AS (
        SELECT 
            c.user_id,
            c.first_order_date,
            c.total_orders,
            c.total_spend,
            -- Days between customer's last order and study end date
            date_diff('day', c.last_order_date, s.end_date) AS recency_days
        FROM customer_raw c
        CROSS JOIN study_end s
    ),
    rfm_scores AS (
        SELECT 
            user_id,
            first_order_date,
            total_orders,
            total_spend,
            recency_days,
            ntile(5) OVER (ORDER BY recency_days DESC) AS r_score, -- 5 is most recent (low days)
            ntile(5) OVER (ORDER BY total_orders ASC) AS f_score, -- 5 is highest frequency
            ntile(5) OVER (ORDER BY total_spend ASC) AS m_score   -- 5 is highest spend
        FROM rfm_base
    ),
    rfm_segments AS (
        SELECT 
            user_id,
            first_order_date,
            total_orders,
            total_spend,
            recency_days,
            r_score,
            f_score,
            m_score,
            CASE 
                WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'Champions'
                WHEN r_score >= 3 AND f_score >= 3 AND m_score >= 3 THEN 'Loyal Customers'
                WHEN r_score >= 4 AND f_score < 3 THEN 'New Customers'
                WHEN r_score < 3 AND f_score >= 3 THEN 'At Risk'
                WHEN r_score <= 2 AND f_score <= 2 THEN 'Lost'
                ELSE 'Need Attention'
            END AS rfm_segment
        FROM rfm_scores
    )
    SELECT 
        user_id,
        first_order_date,
        total_orders,
        total_spend,
        recency_days AS rfm_recency,
        total_orders AS rfm_frequency,
        total_spend AS rfm_monetary,
        rfm_segment,
        total_spend * 1.3 AS clv
    FROM rfm_segments;
    """
    conn.execute(insert_customers_sql)
    
    # 8. Skip Index creation (B-Tree indexes are not needed for DuckDB analytical columnar scans)
    logger.info("Skipping B-Tree index creation (optimizing analytical scans natively)...")
    
    # 9. Create KPI views
    logger.info("Creating KPI views...")
    with open(os.path.join("sql", "gold", "kpi_views.sql"), "r") as f:
        views_sql = f.read()
        for statement in views_sql.split(";"):
            statement_clean = statement.strip()
            if statement_clean:
                conn.execute(statement_clean)
    
    # 10. Create Advanced Analytics views
    logger.info("Creating Advanced Analytics views...")
    import re
    with open(os.path.join("sql", "gold", "advanced_views.sql"), "r") as f:
        adv_sql = f.read()
    # Split on CREATE boundaries (handles comments inside CTEs)
    adv_stmts = re.findall(
        r'(CREATE OR REPLACE VIEW\s+\w+\s+AS.*?)(?=CREATE OR REPLACE VIEW|$)',
        adv_sql, re.DOTALL
    )
    for stmt in adv_stmts:
        stmt = stmt.strip().rstrip(';')
        if stmt:
            conn.execute(stmt)
    logger.info(f"  Created {len(adv_stmts)} advanced analytical views.")

                
    # 10. Print Row counts to verify
    logger.info("Gold Database build complete. Summary of row counts:")
    for table in ["dim_departments", "dim_aisles", "dim_products", "dim_date", "dim_customers", "fact_orders"]:
        cnt = conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        logger.info(f"Table {table}: {cnt:,} rows")
        
    conn.close()
    logger.info("Gold Layer pipeline execution finished successfully!")

def main():
    config = load_config()
    paths = config["paths"]
    
    run_silver_layer(paths)
    run_gold_layer(paths)

if __name__ == "__main__":
    main()
