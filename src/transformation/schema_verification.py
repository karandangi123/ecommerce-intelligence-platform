import os
import yaml
import duckdb
from src.utils.logger import setup_logger

logger = setup_logger("schema_verification")

def load_config(config_path="configs/pipeline_config.yaml"):
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

def verify_gold_layer():
    config = load_config()
    db_path = config["paths"]["gold_db_path"]
    
    logger.info("Connecting to DuckDB for Data Quality & Schema Verification...")
    conn = duckdb.connect(db_path)
    
    tables = {
        "dim_departments": ["department_id", "department"],
        "dim_aisles": ["aisle_id", "aisle"],
        "dim_products": ["product_id", "product_name", "aisle_id", "department_id", "unit_price", "abc_class"],
        "dim_date": ["date_key", "date", "day_of_week", "day_name", "hour_of_day", "is_weekend", "month", "month_name", "year", "quarter"],
        "dim_customers": ["user_id", "first_order_date", "total_orders", "total_spend", "rfm_recency", "rfm_frequency", "rfm_monetary", "rfm_segment", "clv"],
        "fact_orders": ["order_id", "user_id", "product_id", "aisle_id", "department_id", "date_key", "add_to_cart_order", "reordered", "quantity", "unit_price", "subtotal"]
    }
    
    failed_checks = 0
    
    # 1. Verify table presence and schemas
    logger.info("Step 1: Verifying table structures and columns...")
    for table_name, expected_cols in tables.items():
        try:
            # Query column names
            cols_query = conn.execute(f"DESCRIBE {table_name}").df()
            existing_cols = cols_query["column_name"].tolist()
            
            # Check if all expected columns are present
            missing_cols = [c for c in expected_cols if c not in existing_cols]
            if missing_cols:
                logger.error(f"  Table '{table_name}' is missing columns: {missing_cols}")
                failed_checks += 1
            else:
                logger.info(f"  Table '{table_name}' structure matches expected schema.")
        except Exception as e:
            logger.error(f"  Table '{table_name}' check failed: {str(e)}")
            failed_checks += 1
            
    if failed_checks > 0:
        logger.error(f"Schema verification failed with {failed_checks} errors.")
        conn.close()
        return False
        
    # 2. Verify row counts (must be non-empty)
    logger.info("Step 2: Verifying table row counts...")
    for table_name in tables.keys():
        count = conn.execute(f"SELECT count(*) FROM {table_name}").fetchone()[0]
        if count == 0:
            logger.error(f"  Table '{table_name}' is empty!")
            failed_checks += 1
        else:
            logger.info(f"  Table '{table_name}' contains {count:,} rows. [PASSED]")
            
    # 3. Verify Primary Key uniqueness
    logger.info("Step 3: Verifying primary key uniqueness...")
    pk_checks = {
        "dim_departments": "department_id",
        "dim_aisles": "aisle_id",
        "dim_products": "product_id",
        "dim_date": "date_key",
        "dim_customers": "user_id"
    }
    
    for table_name, pk in pk_checks.items():
        total_rows = conn.execute(f"SELECT count(*) FROM {table_name}").fetchone()[0]
        unique_pks = conn.execute(f"SELECT count(distinct {pk}) FROM {table_name}").fetchone()[0]
        if total_rows != unique_pks:
            logger.error(f"  PrimaryKey violation in '{table_name}' on column '{pk}': {total_rows - unique_pks} duplicates found!")
            failed_checks += 1
        else:
            logger.info(f"  PrimaryKey unique check for '{table_name}' on '{pk}' [PASSED]")
            
    # 4. Verify Referential Integrity (Foreign Keys exist in Dimension Tables)
    logger.info("Step 4: Verifying referential integrity (Foreign Key matching)...")
    
    fk_checks = {
        "user_id": ("dim_customers", "user_id"),
        "product_id": ("dim_products", "product_id"),
        "aisle_id": ("dim_aisles", "aisle_id"),
        "department_id": ("dim_departments", "department_id"),
        "date_key": ("dim_date", "date_key")
    }
    
    for fk_col, (dim_table, dim_pk) in fk_checks.items():
        # Count rows in fact table that do not have a matching key in dimension table
        unmatched_query = f"""
            SELECT count(*) 
            FROM fact_orders f
            LEFT JOIN {dim_table} d ON f.{fk_col} = d.{dim_pk}
            WHERE d.{dim_pk} IS NULL
        """
        unmatched_count = conn.execute(unmatched_query).fetchone()[0]
        if unmatched_count > 0:
            logger.error(f"  Referential Integrity violation: {unmatched_count:,} rows in fact_orders.{fk_col} do not exist in {dim_table}.{dim_pk}!")
            failed_checks += 1
        else:
            logger.info(f"  Referential Integrity check: fact_orders.{fk_col} -> {dim_table}.{dim_pk} [PASSED]")
            
    conn.close()
    
    if failed_checks > 0:
        logger.error(f"Data Quality & Schema Verification FAILED with {failed_checks} errors!")
        return False
    else:
        logger.info("Data Quality & Schema Verification PASSED! Gold warehouse is valid and integral.")
        return True

if __name__ == "__main__":
    verify_gold_layer()
