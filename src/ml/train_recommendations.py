import os
import yaml
import duckdb
import polars as pl
import pandas as pd
import numpy as np
from scipy.sparse import csr_matrix
from sklearn.metrics.pairwise import cosine_similarity
# import mlflow
from src.utils.logger import setup_logger

logger = setup_logger("train_recommendations")

def load_config(config_path="configs/pipeline_config.yaml"):
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

def run_association_rules(conn, config):
    logger.info("Starting Market Basket Analysis (Association Rules)...")
    silver_dir = config["paths"]["silver_dir"]
    
    min_support = config["ml"]["apriori"]["min_support"]
    min_confidence = config["ml"]["apriori"]["min_confidence"]
    min_lift = config["ml"]["apriori"]["min_lift"]
    
    # 1. Load data
    logger.info("Loading order_products and orders from silver layer...")
    op_df = pl.read_parquet(os.path.join(silver_dir, "order_products.parquet"))
    orders_df = pl.read_parquet(os.path.join(silver_dir, "orders.parquet"))
    
    total_orders = orders_df.height
    logger.info(f"Total orders: {total_orders:,}. Total line items: {op_df.height:,}")
    
    # To prevent memory bloop, filter for the top 2000 most popular products
    logger.info("Filtering for top 2,000 most popular products to ensure stability...")
    popular_products = op_df.group_by("product_id").len().sort("len", descending=True).head(2000).select("product_id")
    op_df = op_df.join(popular_products, on="product_id", how="inner")
    logger.info(f"Filtered line items count: {op_df.height:,}")
    
    # 2. Get individual product counts for support denominators
    product_counts = op_df.group_by("product_id").len().rename({"len": "product_count"})
    
    # 3. Calculate co-occurrences using self-join
    logger.info("Computing product co-occurrences via Polars self-join...")
    # Self-join on order_id to find pairs in the same cart
    pairs = op_df.join(op_df, on="order_id")
    # Keep only product_id < product_id_right to avoid double counting and self-pairs
    pairs = pairs.filter(pl.col("product_id") < pl.col("product_id_right"))
    # Count pairs
    pair_counts = pairs.group_by(["product_id", "product_id_right"]).len().rename({"len": "pair_count"})
    
    logger.info(f"Generated {pair_counts.height:,} product co-occurrence pairs.")
    
    # 4. Join back individual counts to calculate support, confidence, lift
    logger.info("Calculating Support, Confidence, and Lift metrics...")
    
    # Join count of product A (product_id)
    rules = pair_counts.join(product_counts, on="product_id", how="inner").rename({"product_count": "count_a"})
    
    # Join count of product B (product_id_right)
    rules = rules.join(product_counts, left_on="product_id_right", right_on="product_id", how="inner").rename({"product_count": "count_b"})
    
    # Calculate metrics
    # support(A, B) = pair_count / total_orders
    # confidence(A -> B) = pair_count / count_a
    # confidence(B -> A) = pair_count / count_b
    # lift(A, B) = (pair_count * total_orders) / (count_a * count_b)
    rules = rules.with_columns([
        (pl.col("pair_count") / total_orders).alias("support"),
        (pl.col("pair_count") / pl.col("count_a")).alias("confidence_a_b"),
        (pl.col("pair_count") / pl.col("count_b")).alias("confidence_b_a"),
        ((pl.col("pair_count") * total_orders) / (pl.col("count_a") * pl.col("count_b"))).alias("lift")
    ])
    
    # Filter by thresholds
    rules_filtered = rules.filter(
        (pl.col("support") >= min_support) & 
        ((pl.col("confidence_a_b") >= min_confidence) | (pl.col("confidence_b_a") >= min_confidence)) & 
        (pl.col("lift") >= min_lift)
    ).sort("lift", descending=True)
    
    logger.info(f"Generated {rules_filtered.height:,} rules meeting criteria.")
    
    # Write to DuckDB
    logger.info("Writing association rules to DuckDB...")
    conn.execute("DROP TABLE IF EXISTS association_rules;")
    conn.execute("""
        CREATE TABLE association_rules (
            product_id_a INTEGER,
            product_id_b INTEGER,
            pair_count INTEGER,
            support DOUBLE,
            confidence_a_b DOUBLE,
            confidence_b_a DOUBLE,
            lift DOUBLE
        );
    """)
    
    # Convert to pandas and insert
    rules_pd = rules_filtered.select(["product_id", "product_id_right", "pair_count", "support", "confidence_a_b", "confidence_b_a", "lift"]).to_pandas()
    rules_pd.columns = ["product_id_a", "product_id_b", "pair_count", "support", "confidence_a_b", "confidence_b_a", "lift"]
    
    conn.execute("INSERT INTO association_rules SELECT * FROM rules_pd;")
    logger.info("Association rules successfully loaded in DuckDB!")
    return len(rules_pd)

def run_collaborative_filtering(conn, config):
    logger.info("Starting Collaborative Filtering (Personalized Recommendations)...")
    silver_dir = config["paths"]["silver_dir"]
    
    # 1. Load User-Product interactions
    # To keep model size manageable, filter for the top 5,000 customers and top 1,000 products
    logger.info("Extracting user-product interaction matrix...")
    
    # We will read fact_orders from DuckDB since it is already joined
    interactions = conn.execute("""
        SELECT 
            user_id,
            product_id,
            count(*) as purchase_count
        FROM fact_orders
        WHERE user_id IN (SELECT user_id FROM dim_customers ORDER BY total_orders DESC LIMIT 10000)
          AND product_id IN (SELECT product_id FROM dim_products ORDER BY product_id LIMIT 2000)
        GROUP BY user_id, product_id
    """).df()
    
    if len(interactions) == 0:
        logger.warning("Not enough overlapping user-product interactions for collaborative filtering. Skipping...")
        return
        
    logger.info(f"Building sparse user-product matrix with {len(interactions):,} interactions...")
    
    # Create sparse user-product matrix
    interactions["user_id"] = interactions["user_id"].astype("category")
    interactions["product_id"] = interactions["product_id"].astype("category")
    
    user_cats = interactions["user_id"].cat.categories
    product_cats = interactions["product_id"].cat.categories
    
    row = interactions["user_id"].cat.codes
    col = interactions["product_id"].cat.codes
    data = interactions["purchase_count"].values
    
    # Sparse matrix of shape (users, products)
    matrix = csr_matrix((data, (row, col)), shape=(len(user_cats), len(product_cats)))
    
    # Compute Cosine Similarity between items (products)
    logger.info("Computing item-item cosine similarity matrix...")
    item_similarity = cosine_similarity(matrix.T) # shape: (products, products)
    
    # Store top 10 similar items for each product to save recommendations
    similar_items_list = []
    for idx, product_id in enumerate(product_cats):
        # Sort indices descending by similarity
        similar_indices = np.argsort(item_similarity[idx])[::-1][1:11] # Top 10 similar (exclude self)
        for rank, sim_idx in enumerate(similar_indices):
            similarity = item_similarity[idx][sim_idx]
            if similarity > 0.05: # Only record meaningful similarities
                similar_items_list.append({
                    "product_id": int(product_id),
                    "similar_product_id": int(product_cats[sim_idx]),
                    "similarity_score": float(similarity),
                    "rank": rank + 1
                })
                
    sim_df = pd.DataFrame(similar_items_list)
    logger.info(f"Generated {len(sim_df):,} item similarity records.")
    
    conn.execute("DROP TABLE IF EXISTS product_similarities;")
    conn.execute("""
        CREATE TABLE product_similarities (
            product_id INTEGER,
            similar_product_id INTEGER,
            similarity_score DOUBLE,
            rank INTEGER
        );
    """)
    conn.execute("INSERT INTO product_similarities SELECT * FROM sim_df;")
    
    # 2. Pre-generate personalized recommendations for top 1000 users
    logger.info("Generating personalized recommendations for top users...")
    recs_list = []
    
    # For each user, score candidates based on items they bought and item similarity
    # Score(item) = sum(similarity(item, bought_item) * purchase_count)
    for u_idx in range(min(len(user_cats), 1000)):
        user_id = int(user_cats[u_idx])
        user_vector = matrix[u_idx].toarray()[0]
        bought_indices = np.where(user_vector > 0)[0]
        
        if len(bought_indices) == 0:
            continue
            
        # Multiply user purchase vector by item similarity matrix
        scores = user_vector.dot(item_similarity) # shape: (products,)
        
        # Zero out scores for items already bought
        scores[bought_indices] = 0
        
        # Get top 5 recommendation indices
        top_rec_indices = np.argsort(scores)[::-1][:5]
        
        for rank, r_idx in enumerate(top_rec_indices):
            score = scores[r_idx]
            if score > 0:
                recs_list.append({
                    "user_id": user_id,
                    "product_id": int(product_cats[r_idx]),
                    "recommendation_score": float(score),
                    "rank": rank + 1
                })
                
    recs_df = pd.DataFrame(recs_list)
    logger.info(f"Generated {len(recs_df):,} user recommendation records.")
    
    conn.execute("DROP TABLE IF EXISTS user_recommendations;")
    conn.execute("""
        CREATE TABLE user_recommendations (
            user_id INTEGER,
            product_id INTEGER,
            recommendation_score DOUBLE,
            rank INTEGER
        );
    """)
    conn.execute("INSERT INTO user_recommendations SELECT * FROM recs_df;")
    
    logger.info("Collaborative filtering tables successfully loaded in DuckDB!")
    return len(recs_df)

def main():
    config = load_config()
    db_path = config["paths"]["gold_db_path"]
    
    conn = duckdb.connect(db_path)
    
    num_rules = run_association_rules(conn, config)
    num_recs = run_collaborative_filtering(conn, config)
        
    conn.close()
    logger.info("Recommendations pipeline completed successfully!")

if __name__ == "__main__":
    main()
