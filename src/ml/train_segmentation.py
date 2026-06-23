import os
import yaml
import duckdb
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
# import mlflow
from src.utils.logger import setup_logger

logger = setup_logger("train_segmentation")

def load_config(config_path="configs/pipeline_config.yaml"):
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

def run_clustering():
    config = load_config()
    db_path = config["paths"]["gold_db_path"]
    silver_dir = config["paths"]["silver_dir"]
    
    logger.info("Connecting to DuckDB for Customer Segmentation...")
    conn = duckdb.connect(db_path)
    
    # 1. Load customer RFM metrics
    logger.info("Loading customer RFM data...")
    df = conn.execute("""
        SELECT user_id, rfm_recency, rfm_frequency, rfm_monetary 
        FROM dim_customers
    """).df()
    
    if len(df) == 0:
        logger.error("No customers found in dim_customers. Run medallion pipeline first.")
        conn.close()
        return
        
    logger.info(f"Loaded {len(df):,} customers. Preprocessing features...")
    
    # 2. Preprocess: Log transform to handle right-skewness, then Standard Scale
    # Add 1 to avoid log(0)
    rfm_cols = ["rfm_recency", "rfm_frequency", "rfm_monetary"]
    rfm_log = np.log1p(df[rfm_cols])
    
    scaler = StandardScaler()
    rfm_scaled = scaler.fit_transform(rfm_log)
    
    # 3. Train K-Means and log experiment in MLflow
    n_clusters = 4
    logger.info(f"Training K-Means with {n_clusters} clusters...")
    
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    clusters = kmeans.fit_predict(rfm_scaled)
    
    df["kmeans_cluster"] = clusters
    logger.info(f"K-Means training complete. Inertia: {kmeans.inertia_:.2f}")
        
    # 4. Profile clusters and label them dynamically
    # Calculate means of original features for each cluster to identify cluster properties
    profiles = df.groupby("kmeans_cluster")[rfm_cols].mean()
    logger.info("Cluster profiles (averages):\n" + str(profiles))
    
    # Label mapping:
    # Sort clusters by average monetary value
    sorted_monetary = profiles["rfm_monetary"].sort_values(ascending=False).index.tolist()
    # Sort clusters by average recency (higher recency means less recent, i.e., days since last purchase)
    sorted_recency = profiles["rfm_recency"].sort_values(ascending=True).index.tolist()
    
    cluster_labels = {}
    
    # Highest monetary -> "VIPs / High-Value Loyalists"
    vip_cluster = sorted_monetary[0]
    cluster_labels[vip_cluster] = "VIP / High-Value Loyalist"
    
    # Lowest monetary & highest recency days -> "Lost / Churned"
    lost_cluster = sorted_monetary[-1]
    cluster_labels[lost_cluster] = "Lost Customer"
    
    # Of the remaining two clusters:
    remaining = [c for c in [0, 1, 2, 3] if c not in [vip_cluster, lost_cluster]]
    
    # The one with lower recency (more recent) -> "New / Occasional"
    # The other -> "At Risk / Slipping"
    if profiles.loc[remaining[0], "rfm_recency"] < profiles.loc[remaining[1], "rfm_recency"]:
        cluster_labels[remaining[0]] = "New / Occasional Customer"
        cluster_labels[remaining[1]] = "At Risk / Slipping Customer"
    else:
        cluster_labels[remaining[0]] = "At Risk / Slipping Customer"
        cluster_labels[remaining[1]] = "New / Occasional Customer"
        
    df["kmeans_segment"] = df["kmeans_cluster"].map(cluster_labels)
    
    logger.info("Cluster labels assigned:")
    for cluster_id, label in cluster_labels.items():
        count = (df["kmeans_cluster"] == cluster_id).sum()
        logger.info(f"  Cluster {cluster_id}: {label} ({count:,} customers)")
        
    # 5. Write back to DuckDB dim_customers
    logger.info("Updating dim_customers table with K-Means clusters...")
    
    # Alter table to add columns if they don't exist
    conn.execute("ALTER TABLE dim_customers ADD COLUMN IF NOT EXISTS kmeans_cluster INTEGER;")
    conn.execute("ALTER TABLE dim_customers ADD COLUMN IF NOT EXISTS kmeans_segment VARCHAR;")
    
    temp_parquet = os.path.join(silver_dir, "temp_clusters.parquet")
    df[["user_id", "kmeans_cluster", "kmeans_segment"]].to_parquet(temp_parquet, index=False)
    
    update_sql = f"""
        UPDATE dim_customers
        SET 
            kmeans_cluster = t.kmeans_cluster,
            kmeans_segment = t.kmeans_segment
        FROM read_parquet('{temp_parquet}') t
        WHERE dim_customers.user_id = t.user_id;
    """
    conn.execute(update_sql)
    
    # Clean up temp file
    if os.path.exists(temp_parquet):
        os.remove(temp_parquet)
        
    # Re-verify row counts
    segment_counts = conn.execute("""
        SELECT kmeans_segment, count(*) 
        FROM dim_customers 
        GROUP BY kmeans_segment
    """).fetchall()
    logger.info("Database verification: Customer Segment counts:")
    for seg, count in segment_counts:
        logger.info(f"  {seg}: {count:,}")
        
    conn.close()
    logger.info("Segmentation ML pipeline finished successfully!")

if __name__ == "__main__":
    run_clustering()
