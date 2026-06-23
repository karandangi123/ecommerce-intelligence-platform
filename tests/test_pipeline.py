import os
import yaml
import duckdb
import pytest

def load_config():
    config_path = "configs/pipeline_config.yaml"
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

def test_config_loading():
    """Verify that configuration file is valid and contains required keys."""
    config = load_config()
    assert "paths" in config
    assert "ml" in config
    assert "ai" in config
    assert config["paths"]["gold_db_path"] == "data/gold/ecommerce_analytics.db"

def test_database_connection():
    """Verify that DuckDB database exists and is connectable."""
    config = load_config()
    db_path = config["paths"]["gold_db_path"]
    assert os.path.exists(db_path), f"Database file not found at {db_path}"
    
    conn = duckdb.connect(db_path, read_only=True)
    res = conn.execute("SELECT 1").fetchone()[0]
    assert res == 1
    conn.close()

def test_database_tables():
    """Verify that all required Gold star schema tables exist in DuckDB."""
    config = load_config()
    db_path = config["paths"]["gold_db_path"]
    conn = duckdb.connect(db_path, read_only=True)
    
    tables = conn.execute("SHOW TABLES").fetchall()
    table_names = [t[0] for t in tables]
    
    required_tables = [
        "dim_departments",
        "dim_aisles",
        "dim_products",
        "dim_date",
        "dim_customers",
        "fact_orders"
    ]
    
    for rt in required_tables:
        assert rt in table_names, f"Missing required table: {rt}"
        # Assert non-empty
        count = conn.execute(f"SELECT count(*) FROM {rt}").fetchone()[0]
        assert count > 0, f"Table {rt} is empty"
        
    conn.close()

def test_database_views():
    """Verify that semantic KPI views are created and functional."""
    config = load_config()
    db_path = config["paths"]["gold_db_path"]
    conn = duckdb.connect(db_path, read_only=True)
    
    required_views = [
        "v_executive_kpis",
        "v_customer_analytics",
        "v_product_performance",
        "v_time_patterns"
    ]
    
    # Try querying each view to verify it is valid
    for rv in required_views:
        try:
            conn.execute(f"SELECT * FROM {rv} LIMIT 1").fetchone()
        except Exception as e:
            pytest.fail(f"View {rv} query failed: {str(e)}")
            
    conn.close()

def test_ml_tables():
    """Verify that all machine learning pipeline tables exist, are non-empty, and contain correct schemas."""
    config = load_config()
    db_path = config["paths"]["gold_db_path"]
    conn = duckdb.connect(db_path, read_only=True)
    
    tables = conn.execute("SHOW TABLES").fetchall()
    table_names = [t[0] for t in tables]
    
    required_ml_tables = [
        "daily_anomalies",
        "forecast_predictions",
        "forecast_evaluation",
        "association_rules",
        "product_similarities",
        "user_recommendations"
    ]
    
    for mt in required_ml_tables:
        assert mt in table_names, f"Missing ML table: {mt}"
        
        # Verify the table has data
        count = conn.execute(f"SELECT count(*) FROM {mt}").fetchone()[0]
        assert count > 0, f"ML table {mt} is empty"
        
    # Check daily_anomalies schema and contents
    anom_cols = [c[0] for c in conn.execute("DESCRIBE daily_anomalies").fetchall()]
    assert "is_anomaly" in anom_cols
    assert "anomaly_score" in anom_cols
    
    # Check forecast_predictions schema and contents
    fore_cols = [c[0] for c in conn.execute("DESCRIBE forecast_predictions").fetchall()]
    assert "forecast_date" in fore_cols
    assert "predicted_revenue" in fore_cols
    
    # Check association_rules schema and contents
    assoc_cols = [c[0] for c in conn.execute("DESCRIBE association_rules").fetchall()]
    assert "lift" in assoc_cols
    assert "confidence_a_b" in assoc_cols
    
    conn.close()

def test_data_quality_tables():
    """Verify that the Data Quality framework tables exist and contain valid scored results."""
    config = load_config()
    db_path = config["paths"]["gold_db_path"]
    conn = duckdb.connect(db_path, read_only=True)

    tables = conn.execute("SHOW TABLES").fetchall()
    table_names = [t[0] for t in tables]

    # 1. Verify DQ tables exist
    dq_tables = ["dq_table_scores", "dq_column_detail", "dq_issues"]
    for dt in dq_tables:
        assert dt in table_names, f"Missing DQ table: {dt}"

    # 2. Verify dq_table_scores has rows and correct schema
    scores_df = conn.execute("SELECT * FROM dq_table_scores").df()
    assert len(scores_df) >= 6, "dq_table_scores should have at least 6 rows (one per table)"
    required_score_cols = [
        "table_name", "overall_dq_score", "completeness_score",
        "uniqueness_score", "validity_score", "consistency_score",
        "freshness_score", "total_checks", "passed_checks", "failed_checks"
    ]
    for col in required_score_cols:
        assert col in scores_df.columns, f"Missing column in dq_table_scores: {col}"

    # 3. Verify scores are within valid range [0, 100]
    for _, row in scores_df.iterrows():
        assert 0 <= row["overall_dq_score"] <= 100, f"Invalid DQ score for {row['table_name']}"

    # 4. Verify dq_column_detail has rows (should have 100+ profiling entries)
    detail_count = conn.execute("SELECT count(*) FROM dq_column_detail").fetchone()[0]
    assert detail_count >= 100, f"dq_column_detail only has {detail_count} rows, expected 100+"

    # 5. Verify all 6 DQ dimensions are represented
    dimensions = conn.execute(
        "SELECT DISTINCT dimension FROM dq_column_detail ORDER BY dimension"
    ).fetchall()
    dim_names = [d[0] for d in dimensions]
    expected_dims = ["completeness", "consistency", "freshness", "statistical", "uniqueness", "validity"]
    for ed in expected_dims:
        assert ed in dim_names, f"Missing DQ dimension: {ed}"

    # 6. Verify dq_issues table is queryable (may have 0 rows if data is clean)
    conn.execute("SELECT * FROM dq_issues LIMIT 1")

    conn.close()

def test_advanced_analytics_views():
    """Verify that all 13 advanced analytics views exist, are queryable, and return data."""
    config = load_config()
    db_path = config["paths"]["gold_db_path"]
    conn = duckdb.connect(db_path, read_only=True)

    advanced_views = {
        "v_cohort_retention": ["cohort_month", "month_number", "active_customers", "retention_rate_pct"],
        "v_monthly_kpis": ["month", "revenue", "orders", "avg_order_value", "revenue_growth_pct"],
        "v_cart_analysis": ["cart_size_bucket", "order_count", "avg_cart_value", "avg_items"],
        "v_reorder_behavior": ["department", "aisle", "reorder_rate_pct"],
        "v_department_penetration": ["department", "penetration_pct", "department_revenue"],
        "v_customer_ltv": ["user_id", "projected_annual_clv", "clv_tier"],
        "v_rfm_revenue_matrix": ["r_score", "f_score", "avg_monetary", "customer_count"],
        "v_day_hour_heatmap": ["day_of_week", "hour_of_day", "order_count", "revenue"],
        "v_purchase_frequency": ["frequency_bucket", "customer_count", "revenue_pct"],
        "v_revenue_concentration": ["revenue_rank", "cumulative_revenue_pct"],
        "v_segment_summary": ["rfm_segment", "customers", "avg_spend", "revenue_share_pct"],
        "v_product_trends": ["month", "product_id", "revenue", "revenue_growth_pct"],
        "v_department_cross_sell": ["department_a", "department_b", "pct_of_a_also_buy_b"],
    }

    for view_name, expected_cols in advanced_views.items():
        # 1. View must be queryable
        try:
            df = conn.execute(f"SELECT * FROM {view_name} LIMIT 5").df()
        except Exception as e:
            pytest.fail(f"View {view_name} query failed: {str(e)}")

        # 2. View must return rows
        assert len(df) > 0, f"View {view_name} returned 0 rows"

        # 3. View must contain expected columns
        for col in expected_cols:
            assert col in df.columns, f"View {view_name} missing column: {col}"

    conn.close()
