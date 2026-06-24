"""
Thin Python loader — loads Olist CSVs into PostgreSQL raw tables.
ALL business logic lives in SQL. This file just moves data.
"""
import os
import csv
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# Database connection
def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )

# CSV files and their target table names
CSV_TABLE_MAP = {
    "olist_orders_dataset.csv": "raw_orders",
    "olist_order_items_dataset.csv": "raw_order_items",
    "olist_order_payments_dataset.csv": "raw_order_payments",
    "olist_order_reviews_dataset.csv": "raw_order_reviews",
    "olist_customers_dataset.csv": "raw_customers",
    "olist_products_dataset.csv": "raw_products",
    "olist_sellers_dataset.csv": "raw_sellers",
    "olist_geolocation_dataset.csv": "raw_geolocation",
    "product_category_name_translation.csv": "raw_category_translation",
}

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")


def load_csv_to_table(filepath, table_name, conn):
    """Load a CSV file into a PostgreSQL table. Creates table from CSV headers."""
    
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        headers = next(reader)  # First row = column names
    
    # Clean column names (remove spaces, lowercase)
    columns = [h.strip().lower().replace(" ", "_") for h in headers]
    
    cur = conn.cursor()
    
    # Drop table if exists, create with all TEXT columns (we clean types in SQL later)
    cur.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE;")
    col_defs = ", ".join([f'"{c}" TEXT' for c in columns])
    cur.execute(f"CREATE TABLE {table_name} ({col_defs});")
    
    # Use COPY for fast bulk loading
    with open(filepath, "r", encoding="utf-8") as f:
        cur.copy_expert(
            f"COPY {table_name} FROM STDIN WITH CSV HEADER ENCODING 'UTF-8'",
            f
        )
    
    # Get row count
    cur.execute(f"SELECT COUNT(*) FROM {table_name};")
    count = cur.fetchone()[0]
    
    conn.commit()
    cur.close()
    
    return count


def main():
    conn = get_connection()
    print("=" * 60)
    print("LOADING OLIST DATA INTO POSTGRESQL")
    print("=" * 60)
    
    total_rows = 0
    
    for csv_file, table_name in CSV_TABLE_MAP.items():
        filepath = os.path.join(DATA_DIR, csv_file)
        
        if not os.path.exists(filepath):
            print(f"  ⚠️  MISSING: {csv_file}")
            continue
        
        count = load_csv_to_table(filepath, table_name, conn)
        total_rows += count
        print(f"  ✅ {table_name:<30} → {count:>10,} rows")
    
    print("=" * 60)
    print(f"  TOTAL: {total_rows:,} rows loaded")
    print("=" * 60)
    
    conn.close()


if __name__ == "__main__":
    main()
