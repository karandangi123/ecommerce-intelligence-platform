import duckdb
import os
import pandas as pd

def export_cache():
    print("Exporting dashboard data to static cache for cloud deployment...")
    db_path = "data/gold/ecommerce_analytics.db"
    cache_dir = "data/dashboard_cache"
    os.makedirs(cache_dir, exist_ok=True)
    
    conn = duckdb.connect(db_path, read_only=True)
    
    tables_to_export = [
        "dim_departments",
        "v_monthly_kpis",
        "daily_anomalies",
        "v_cohort_retention",
        "v_rfm_revenue_matrix",
        "v_customer_ltv",
        "v_segment_summary",
        "v_purchase_frequency",
        "v_revenue_concentration",
        "v_department_penetration",
        "v_reorder_behavior",
        "v_product_trends",
        "v_cart_analysis",
        "v_day_hour_heatmap",
        "association_rules",
        "v_department_cross_sell",
        "dq_table_scores"
    ]
    
    for table in tables_to_export:
        try:
            df = conn.execute(f"SELECT * FROM {table}").df()
            out_path = os.path.join(cache_dir, f"{table}.parquet")
            df.to_parquet(out_path, index=False)
            print(f"  ✓ Exported {table} ({len(df)} rows)")
        except Exception as e:
            print(f"  ✗ Failed to export {table}: {e}")
            
    conn.close()
    print(f"Cache export complete! Files saved to {cache_dir}")

if __name__ == "__main__":
    export_cache()
