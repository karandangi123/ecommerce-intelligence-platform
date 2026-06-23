"""
Data Quality Report Engine
==========================
Enterprise-grade data quality framework that evaluates the Gold warehouse
across 6 quality dimensions and produces scored, actionable reports.

DQ Dimensions:
  1. Completeness  — % of non-null values per column
  2. Uniqueness    — duplicate detection at row and column level
  3. Validity      — value range and domain checks
  4. Consistency   — cross-table referential integrity
  5. Freshness     — data recency vs current date
  6. Statistical   — distribution profiling (min, max, mean, median, std, skew)

Output Tables (written to DuckDB):
  - dq_table_scores:   per-table aggregate quality scores
  - dq_column_detail:  per-column profiling metrics
  - dq_issues:         specific flagged rows with issue descriptions
"""
import os
import yaml
import duckdb
import pandas as pd
import numpy as np
from datetime import datetime, date
from src.utils.logger import setup_logger

logger = setup_logger("data_quality")

def load_config(config_path="configs/pipeline_config.yaml"):
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


# ─────────────────────────────────────────────────────────────────────────────
# DIMENSION 1: COMPLETENESS
# ─────────────────────────────────────────────────────────────────────────────
def check_completeness(conn, table_name, columns):
    """Calculate % non-null for every column in a table."""
    results = []
    total_rows = conn.execute(f"SELECT count(*) FROM {table_name}").fetchone()[0]
    if total_rows == 0:
        return results

    for col in columns:
        non_null = conn.execute(
            f"SELECT count({col}) FROM {table_name} WHERE {col} IS NOT NULL"
        ).fetchone()[0]
        pct = round((non_null / total_rows) * 100, 2)
        results.append({
            "table_name": table_name,
            "column_name": col,
            "dimension": "completeness",
            "metric_name": "non_null_pct",
            "metric_value": pct,
            "passed": pct >= 99.0  # threshold: 99% non-null
        })
    return results


# ─────────────────────────────────────────────────────────────────────────────
# DIMENSION 2: UNIQUENESS
# ─────────────────────────────────────────────────────────────────────────────
def check_uniqueness(conn, table_name, columns, primary_keys):
    """Check column cardinality and detect exact duplicate rows."""
    results = []
    total_rows = conn.execute(f"SELECT count(*) FROM {table_name}").fetchone()[0]
    if total_rows == 0:
        return results, []

    issues = []

    # Per-column uniqueness ratio
    for col in columns:
        distinct_count = conn.execute(
            f"SELECT count(DISTINCT {col}) FROM {table_name}"
        ).fetchone()[0]
        uniqueness_pct = round((distinct_count / total_rows) * 100, 4)
        results.append({
            "table_name": table_name,
            "column_name": col,
            "dimension": "uniqueness",
            "metric_name": "distinct_pct",
            "metric_value": uniqueness_pct,
            "passed": True  # informational, no pass/fail threshold
        })

    # Primary key duplicate check
    if primary_keys:
        pk_cols = ", ".join(primary_keys)
        dup_count = conn.execute(f"""
            SELECT count(*) FROM (
                SELECT {pk_cols}, count(*) as cnt
                FROM {table_name}
                GROUP BY {pk_cols}
                HAVING count(*) > 1
            )
        """).fetchone()[0]
        results.append({
            "table_name": table_name,
            "column_name": pk_cols,
            "dimension": "uniqueness",
            "metric_name": "pk_duplicate_groups",
            "metric_value": dup_count,
            "passed": dup_count == 0
        })
        if dup_count > 0:
            issues.append({
                "table_name": table_name,
                "issue_type": "DUPLICATE_PRIMARY_KEY",
                "severity": "CRITICAL",
                "description": f"{dup_count} duplicate groups found on primary key ({pk_cols})",
                "affected_rows": dup_count
            })

    return results, issues


# ─────────────────────────────────────────────────────────────────────────────
# DIMENSION 3: VALIDITY
# ─────────────────────────────────────────────────────────────────────────────
def check_validity(conn):
    """Domain-specific range and value checks."""
    results = []
    issues = []

    validity_rules = [
        # (table, column, condition_for_valid, rule_description)
        ("fact_orders", "unit_price", "unit_price > 0", "Unit price must be positive"),
        ("fact_orders", "subtotal", "subtotal > 0", "Subtotal must be positive"),
        ("fact_orders", "quantity", "quantity > 0", "Quantity must be positive"),
        ("fact_orders", "reordered", "reordered IN (0, 1)", "Reordered must be 0 or 1"),
        ("fact_orders", "add_to_cart_order", "add_to_cart_order > 0", "Cart order must be positive"),
        ("dim_date", "hour_of_day", "hour_of_day BETWEEN 0 AND 23", "Hour must be 0-23"),
        ("dim_date", "day_of_week", "day_of_week BETWEEN 0 AND 6", "Day of week must be 0-6"),
        ("dim_date", "month", "month BETWEEN 1 AND 12", "Month must be 1-12"),
        ("dim_date", "year", "year BETWEEN 2024 AND 2027", "Year must be in expected range"),
        ("dim_products", "unit_price", "unit_price > 0 AND unit_price < 100", "Product price must be $0-$100"),
        ("dim_customers", "total_orders", "total_orders > 0", "Customer must have at least 1 order"),
        ("dim_customers", "total_spend", "total_spend > 0", "Customer spend must be positive"),
        ("dim_customers", "rfm_recency", "rfm_recency >= 0", "Recency days must be non-negative"),
        ("dim_customers", "clv", "clv > 0", "CLV must be positive"),
    ]

    for table, column, condition, description in validity_rules:
        total = conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        valid = conn.execute(
            f"SELECT count(*) FROM {table} WHERE {condition}"
        ).fetchone()[0]
        invalid = total - valid
        pct = round((valid / total) * 100, 4) if total > 0 else 0

        results.append({
            "table_name": table,
            "column_name": column,
            "dimension": "validity",
            "metric_name": f"valid_pct ({description})",
            "metric_value": pct,
            "passed": pct >= 99.9
        })

        if invalid > 0:
            issues.append({
                "table_name": table,
                "issue_type": "VALIDITY_VIOLATION",
                "severity": "WARNING" if invalid < 100 else "CRITICAL",
                "description": f"{invalid:,} rows fail rule: '{description}' on column {column}",
                "affected_rows": invalid
            })

    return results, issues


# ─────────────────────────────────────────────────────────────────────────────
# DIMENSION 4: CONSISTENCY (Referential Integrity)
# ─────────────────────────────────────────────────────────────────────────────
def check_consistency(conn):
    """Verify all foreign keys in fact_orders reference existing dimension rows."""
    results = []
    issues = []

    fk_checks = {
        "user_id": ("dim_customers", "user_id"),
        "product_id": ("dim_products", "product_id"),
        "aisle_id": ("dim_aisles", "aisle_id"),
        "department_id": ("dim_departments", "department_id"),
        "date_key": ("dim_date", "date_key"),
    }

    total_fact = conn.execute("SELECT count(*) FROM fact_orders").fetchone()[0]

    for fk_col, (dim_table, dim_pk) in fk_checks.items():
        orphans = conn.execute(f"""
            SELECT count(*)
            FROM fact_orders f
            LEFT JOIN {dim_table} d ON f.{fk_col} = d.{dim_pk}
            WHERE d.{dim_pk} IS NULL
        """).fetchone()[0]

        pct_valid = round(((total_fact - orphans) / total_fact) * 100, 4) if total_fact > 0 else 0

        results.append({
            "table_name": "fact_orders",
            "column_name": fk_col,
            "dimension": "consistency",
            "metric_name": f"fk_integrity -> {dim_table}.{dim_pk}",
            "metric_value": pct_valid,
            "passed": orphans == 0
        })

        if orphans > 0:
            issues.append({
                "table_name": "fact_orders",
                "issue_type": "ORPHANED_FOREIGN_KEY",
                "severity": "CRITICAL",
                "description": f"{orphans:,} rows in fact_orders.{fk_col} have no match in {dim_table}.{dim_pk}",
                "affected_rows": orphans
            })

    return results, issues


# ─────────────────────────────────────────────────────────────────────────────
# DIMENSION 5: FRESHNESS
# ─────────────────────────────────────────────────────────────────────────────
def check_freshness(conn):
    """Check how recent the data is compared to the current date."""
    results = []
    issues = []

    max_date = conn.execute("SELECT max(date) FROM dim_date").fetchone()[0]
    today = date.today()

    if max_date:
        staleness_days = (today - max_date).days
        results.append({
            "table_name": "dim_date",
            "column_name": "date",
            "dimension": "freshness",
            "metric_name": "staleness_days",
            "metric_value": staleness_days,
            "passed": staleness_days <= 7  # data should be within 7 days
        })
        results.append({
            "table_name": "dim_date",
            "column_name": "date",
            "dimension": "freshness",
            "metric_name": "max_date",
            "metric_value": max_date.isoformat(),
            "passed": True
        })

        if staleness_days > 7:
            issues.append({
                "table_name": "dim_date",
                "issue_type": "STALE_DATA",
                "severity": "WARNING",
                "description": f"Most recent data is {staleness_days} days old (max_date: {max_date}). Expected within 7 days.",
                "affected_rows": 0
            })

    # Check order date range span
    min_date = conn.execute("SELECT min(date) FROM dim_date").fetchone()[0]
    if min_date and max_date:
        span_days = (max_date - min_date).days
        results.append({
            "table_name": "dim_date",
            "column_name": "date",
            "dimension": "freshness",
            "metric_name": "date_span_days",
            "metric_value": span_days,
            "passed": True
        })

    return results, issues


# ─────────────────────────────────────────────────────────────────────────────
# DIMENSION 6: STATISTICAL PROFILING
# ─────────────────────────────────────────────────────────────────────────────
def profile_numeric_columns(conn):
    """Compute descriptive statistics for key numeric columns."""
    results = []

    profile_targets = [
        ("fact_orders", "unit_price"),
        ("fact_orders", "subtotal"),
        ("fact_orders", "add_to_cart_order"),
        ("dim_customers", "total_orders"),
        ("dim_customers", "total_spend"),
        ("dim_customers", "rfm_recency"),
        ("dim_customers", "clv"),
        ("dim_products", "unit_price"),
    ]

    for table, col in profile_targets:
        try:
            stats = conn.execute(f"""
                SELECT
                    count({col}) as cnt,
                    min({col}) as min_val,
                    max({col}) as max_val,
                    avg({col}) as mean_val,
                    approx_quantile({col}, 0.5) as median_val,
                    stddev({col}) as std_val,
                    approx_quantile({col}, 0.25) as p25,
                    approx_quantile({col}, 0.75) as p75,
                    approx_quantile({col}, 0.95) as p95,
                    approx_quantile({col}, 0.99) as p99
                FROM {table}
            """).df().iloc[0]

            for metric_name in ["cnt", "min_val", "max_val", "mean_val", "median_val",
                                "std_val", "p25", "p75", "p95", "p99"]:
                val = stats[metric_name]
                results.append({
                    "table_name": table,
                    "column_name": col,
                    "dimension": "statistical",
                    "metric_name": metric_name,
                    "metric_value": round(float(val), 4) if val is not None else 0,
                    "passed": True
                })
        except Exception as e:
            logger.warning(f"Could not profile {table}.{col}: {e}")

    return results


# ─────────────────────────────────────────────────────────────────────────────
# AGGREGATE DQ SCORE COMPUTATION
# ─────────────────────────────────────────────────────────────────────────────
def compute_table_scores(all_results):
    """
    Compute a weighted DQ score per table.
    Weights: completeness=30%, uniqueness=20%, validity=25%,
             consistency=15%, freshness=10%
    """
    weights = {
        "completeness": 0.30,
        "uniqueness": 0.20,
        "validity": 0.25,
        "consistency": 0.15,
        "freshness": 0.10,
    }

    # Group results by table and dimension
    table_dim_scores = {}
    for r in all_results:
        table = r["table_name"]
        dim = r["dimension"]
        if dim == "statistical":
            continue  # statistical profiling is informational, not scored

        if table not in table_dim_scores:
            table_dim_scores[table] = {}
        if dim not in table_dim_scores[table]:
            table_dim_scores[table][dim] = {"pass": 0, "total": 0}

        table_dim_scores[table][dim]["total"] += 1
        if r["passed"]:
            table_dim_scores[table][dim]["pass"] += 1

    # Calculate weighted score per table
    table_scores = []
    for table, dims in table_dim_scores.items():
        weighted_sum = 0
        weight_sum = 0
        dim_breakdown = {}

        for dim, counts in dims.items():
            dim_score = (counts["pass"] / counts["total"]) * 100 if counts["total"] > 0 else 100
            dim_breakdown[dim] = round(dim_score, 1)
            w = weights.get(dim, 0.1)
            weighted_sum += dim_score * w
            weight_sum += w

        overall = round(weighted_sum / weight_sum, 1) if weight_sum > 0 else 0

        table_scores.append({
            "table_name": table,
            "overall_dq_score": overall,
            "completeness_score": dim_breakdown.get("completeness", 100.0),
            "uniqueness_score": dim_breakdown.get("uniqueness", 100.0),
            "validity_score": dim_breakdown.get("validity", 100.0),
            "consistency_score": dim_breakdown.get("consistency", 100.0),
            "freshness_score": dim_breakdown.get("freshness", 100.0),
            "total_checks": sum(c["total"] for c in dims.values()),
            "passed_checks": sum(c["pass"] for c in dims.values()),
            "failed_checks": sum(c["total"] - c["pass"] for c in dims.values()),
        })

    return table_scores


# ─────────────────────────────────────────────────────────────────────────────
# MAIN ORCHESTRATOR
# ─────────────────────────────────────────────────────────────────────────────
def run_data_quality_report():
    config = load_config()
    db_path = config["paths"]["gold_db_path"]

    logger.info("=" * 70)
    logger.info("  DATA QUALITY REPORT ENGINE — Starting Full Warehouse Audit")
    logger.info("=" * 70)

    conn = duckdb.connect(db_path)

    # Define table schemas for profiling
    table_schemas = {
        "dim_departments": {
            "columns": ["department_id", "department"],
            "primary_keys": ["department_id"]
        },
        "dim_aisles": {
            "columns": ["aisle_id", "aisle"],
            "primary_keys": ["aisle_id"]
        },
        "dim_products": {
            "columns": ["product_id", "product_name", "aisle_id", "department_id", "unit_price", "abc_class"],
            "primary_keys": ["product_id"]
        },
        "dim_date": {
            "columns": ["date_key", "date", "day_of_week", "day_name", "hour_of_day",
                         "is_weekend", "month", "month_name", "year", "quarter"],
            "primary_keys": ["date_key"]
        },
        "dim_customers": {
            "columns": ["user_id", "first_order_date", "total_orders", "total_spend",
                         "rfm_recency", "rfm_frequency", "rfm_monetary", "rfm_segment", "clv"],
            "primary_keys": ["user_id"]
        },
        "fact_orders": {
            "columns": ["order_id", "user_id", "product_id", "aisle_id", "department_id",
                         "date_key", "add_to_cart_order", "reordered", "quantity", "unit_price", "subtotal"],
            "primary_keys": ["order_id", "product_id"]
        },
    }

    all_results = []
    all_issues = []

    # ── Dimension 1: Completeness ──
    logger.info("Dimension 1/6: COMPLETENESS — Scanning for NULL values...")
    for table, schema in table_schemas.items():
        results = check_completeness(conn, table, schema["columns"])
        all_results.extend(results)
        nulls_found = sum(1 for r in results if not r["passed"])
        status = "PASSED" if nulls_found == 0 else f"FAILED ({nulls_found} columns below threshold)"
        logger.info(f"  {table}: {status}")

    # ── Dimension 2: Uniqueness ──
    logger.info("Dimension 2/6: UNIQUENESS — Checking cardinality and duplicates...")
    for table, schema in table_schemas.items():
        results, issues = check_uniqueness(conn, table, schema["columns"], schema["primary_keys"])
        all_results.extend(results)
        all_issues.extend(issues)
        dup_issues = sum(1 for i in issues if i["issue_type"] == "DUPLICATE_PRIMARY_KEY")
        status = "PASSED" if dup_issues == 0 else f"FAILED ({dup_issues} duplicate PKs)"
        logger.info(f"  {table}: {status}")

    # ── Dimension 3: Validity ──
    logger.info("Dimension 3/6: VALIDITY — Enforcing domain rules...")
    results, issues = check_validity(conn)
    all_results.extend(results)
    all_issues.extend(issues)
    fails = sum(1 for r in results if not r["passed"])
    logger.info(f"  {len(results)} rules checked, {fails} failed")

    # ── Dimension 4: Consistency ──
    logger.info("Dimension 4/6: CONSISTENCY — Verifying referential integrity...")
    results, issues = check_consistency(conn)
    all_results.extend(results)
    all_issues.extend(issues)
    orphans = sum(1 for r in results if not r["passed"])
    logger.info(f"  {len(results)} FK checks, {orphans} orphaned")

    # ── Dimension 5: Freshness ──
    logger.info("Dimension 5/6: FRESHNESS — Checking data recency...")
    results, issues = check_freshness(conn)
    all_results.extend(results)
    all_issues.extend(issues)
    for r in results:
        if r["metric_name"] == "staleness_days":
            logger.info(f"  Data staleness: {r['metric_value']} days")
        elif r["metric_name"] == "date_span_days":
            logger.info(f"  Date range span: {r['metric_value']} days")

    # ── Dimension 6: Statistical Profiling ──
    logger.info("Dimension 6/6: STATISTICAL PROFILING — Computing distributions...")
    results = profile_numeric_columns(conn)
    all_results.extend(results)
    logger.info(f"  Profiled {len(results)} numeric column statistics")

    # ── Compute Aggregate Scores ──
    logger.info("Computing weighted DQ scores per table...")
    table_scores = compute_table_scores(all_results)

    # ── Write Results to DuckDB ──
    logger.info("Writing DQ results to DuckDB tables...")

    # Table 1: dq_table_scores
    conn.execute("DROP TABLE IF EXISTS dq_table_scores")
    conn.execute("""
        CREATE TABLE dq_table_scores (
            table_name VARCHAR,
            overall_dq_score DOUBLE,
            completeness_score DOUBLE,
            uniqueness_score DOUBLE,
            validity_score DOUBLE,
            consistency_score DOUBLE,
            freshness_score DOUBLE,
            total_checks INTEGER,
            passed_checks INTEGER,
            failed_checks INTEGER
        )
    """)
    scores_df = pd.DataFrame(table_scores)
    conn.execute("INSERT INTO dq_table_scores SELECT * FROM scores_df")

    # Table 2: dq_column_detail
    conn.execute("DROP TABLE IF EXISTS dq_column_detail")
    conn.execute("""
        CREATE TABLE dq_column_detail (
            table_name VARCHAR,
            column_name VARCHAR,
            dimension VARCHAR,
            metric_name VARCHAR,
            metric_value VARCHAR,
            passed BOOLEAN
        )
    """)
    detail_records = []
    for r in all_results:
        detail_records.append({
            "table_name": r["table_name"],
            "column_name": r["column_name"],
            "dimension": r["dimension"],
            "metric_name": r["metric_name"],
            "metric_value": str(r["metric_value"]),
            "passed": r["passed"]
        })
    detail_df = pd.DataFrame(detail_records)
    conn.execute("INSERT INTO dq_column_detail SELECT * FROM detail_df")

    # Table 3: dq_issues
    conn.execute("DROP TABLE IF EXISTS dq_issues")
    conn.execute("""
        CREATE TABLE dq_issues (
            table_name VARCHAR,
            issue_type VARCHAR,
            severity VARCHAR,
            description VARCHAR,
            affected_rows INTEGER
        )
    """)
    if all_issues:
        issues_df = pd.DataFrame(all_issues)
        conn.execute("INSERT INTO dq_issues SELECT * FROM issues_df")

    # ── Print Summary ──
    logger.info("")
    logger.info("=" * 70)
    logger.info("  DATA QUALITY REPORT — SUMMARY")
    logger.info("=" * 70)

    overall_scores = []
    for ts in table_scores:
        logger.info(
            f"  {ts['table_name']:20s}  DQ Score: {ts['overall_dq_score']:6.1f}%  "
            f"({ts['passed_checks']}/{ts['total_checks']} checks passed)"
        )
        overall_scores.append(ts["overall_dq_score"])

    warehouse_score = round(np.mean(overall_scores), 1) if overall_scores else 0
    logger.info(f"\n  WAREHOUSE OVERALL DQ SCORE: {warehouse_score}%")

    if all_issues:
        logger.info(f"\n  ISSUES FLAGGED: {len(all_issues)}")
        for issue in all_issues:
            logger.info(f"    [{issue['severity']}] {issue['table_name']}: {issue['description']}")
    else:
        logger.info("\n  NO ISSUES FLAGGED — Warehouse is clean.")

    logger.info("=" * 70)

    conn.close()
    logger.info("Data Quality Report completed and saved to DuckDB.")
    return warehouse_score


if __name__ == "__main__":
    run_data_quality_report()
