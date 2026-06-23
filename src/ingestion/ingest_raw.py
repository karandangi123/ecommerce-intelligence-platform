import os
import shutil
import yaml
import polars as pl
from src.utils.logger import setup_logger

logger = setup_logger("ingestion")

def load_config(config_path="configs/pipeline_config.yaml"):
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

def ingest_file(src_path, dest_csv_path, dest_parquet_path):
    logger.info(f"Ingesting {os.path.basename(src_path)}...")
    
    # 1. Copy raw CSV to data/raw as backup/record
    if not os.path.exists(dest_csv_path):
        logger.info(f"Copying {os.path.basename(src_path)} to {dest_csv_path}...")
        shutil.copy2(src_path, dest_csv_path)
    
    # 2. Read with Polars and write to Parquet (Bronze Layer)
    logger.info(f"Reading {dest_csv_path} and writing to {dest_parquet_path}...")
    df = pl.read_csv(dest_csv_path)
    df.write_parquet(dest_parquet_path, compression="snappy")
    
    logger.info(f"Successfully ingested {os.path.basename(src_path)}. Rows: {df.height}, Columns: {df.width}")
    return df.height

def main():
    config = load_config()
    paths = config["paths"]
    
    archive_dir = paths["source_archive_dir"]
    raw_dir = paths["raw_dir"]
    bronze_dir = paths["bronze_dir"]
    
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(bronze_dir, exist_ok=True)
    
    csv_files = [
        "departments.csv",
        "aisles.csv",
        "products.csv",
        "orders.csv",
        "order_products__prior.csv",
        "order_products__train.csv"
    ]
    
    logger.info("Starting Bronze Layer Ingestion pipeline...")
    
    for filename in csv_files:
        src_path = os.path.join(archive_dir, filename)
        dest_csv_path = os.path.join(raw_dir, filename)
        dest_parquet_path = os.path.join(bronze_dir, filename.replace(".csv", ".parquet"))
        
        if not os.path.exists(src_path):
            logger.error(f"Required source file not found in archive: {src_path}")
            raise FileNotFoundError(f"Missing file: {src_path}")
            
        ingest_file(src_path, dest_csv_path, dest_parquet_path)
        
    logger.info("Bronze Layer Ingestion pipeline completed successfully!")

if __name__ == "__main__":
    main()
