import os
import yaml
import duckdb
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
# import mlflow
from src.utils.logger import setup_logger

logger = setup_logger("anomaly_detection")

def load_config(config_path="configs/pipeline_config.yaml"):
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

def run_anomaly_detection():
    config = load_config()
    db_path = config["paths"]["gold_db_path"]
    contamination = config["ml"]["anomaly"]["contamination"]
    
    logger.info("Connecting to DuckDB for Anomaly Detection...")
    conn = duckdb.connect(db_path)
    
    # 1. Aggregate orders and revenue to a daily grain
    logger.info("Extracting daily aggregated transaction metrics...")
    query = """
        SELECT 
            d.date,
            count(distinct f.order_id) AS order_count,
            sum(f.subtotal) AS revenue
        FROM fact_orders f
        JOIN dim_date d ON f.date_key = d.date_key
        GROUP BY d.date
        ORDER BY d.date
    """
    df = conn.execute(query).df()
    
    if len(df) == 0:
        logger.error("No daily data found. Run medallion pipeline first.")
        conn.close()
        return
        
    df["date"] = pd.to_datetime(df["date"])
    
    logger.info(f"Loaded {len(df)} days of historical transaction aggregates. Training Isolation Forest...")
    
    # 2. Extract features: order_count, revenue
    X = df[["order_count", "revenue"]].values
    
    model = IsolationForest(contamination=contamination, random_state=42)
    # fit_predict returns 1 for inliers, -1 for outliers
    preds = model.fit_predict(X)
    scores = model.decision_function(X) # lower score means more anomalous
    
    df["is_anomaly"] = np.where(preds == -1, 1, 0)
    df["anomaly_score"] = scores
    
    logger.info(f"Anomaly detection complete. Flagged {df['is_anomaly'].sum()} anomalies out of {len(df)} days.")
        
    # 3. Save anomalies back to DuckDB table: daily_anomalies
    logger.info("Writing anomalies back to DuckDB...")
    
    # Convert dates to strings for database compatibility
    df_db = df.copy()
    df_db["date"] = df_db["date"].dt.strftime("%Y-%m-%d")
    
    conn.execute("DROP TABLE IF EXISTS daily_anomalies;")
    conn.execute("""
        CREATE TABLE daily_anomalies (
            date DATE PRIMARY KEY,
            order_count INTEGER,
            revenue DOUBLE,
            is_anomaly INTEGER,
            anomaly_score DOUBLE
        );
    """)
    
    # Insert from pandas dataframe
    conn.execute("INSERT INTO daily_anomalies SELECT * FROM df_db")
    
    logger.info("Daily anomalies successfully saved to database:")
    sample = conn.execute("SELECT * FROM daily_anomalies WHERE is_anomaly = 1 LIMIT 5").df()
    logger.info("\n" + str(sample))
    
    conn.close()
    logger.info("Anomaly detection pipeline completed successfully!")

if __name__ == "__main__":
    run_anomaly_detection()
