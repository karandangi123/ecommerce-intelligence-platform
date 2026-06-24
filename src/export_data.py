"""
Export Utility — Runs SQL queries on our analytical views and exports them to JSON files.
This feeds our zero-dependency HTML dashboard.
"""
import os
import json
import decimal
import datetime
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# Helper to handle SQL data types not native to JSON (Decimals and Dates)
class DashboardJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.isoformat()
        return super(DashboardJsonEncoder, self).default(obj)

def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )

EXPORT_QUERIES = {
    # 1. CEO view data
    "ceo_monthly.json": "SELECT * FROM view_ceo_monthly_kpis ORDER BY order_month ASC;",
    
    # 2. Operations view data
    "ops_monthly.json": "SELECT * FROM view_ops_monthly_kpis ORDER BY order_month ASC;",
    
    # 3. Marketing view data
    "marketing_monthly.json": "SELECT * FROM view_marketing_monthly_kpis ORDER BY order_month ASC;",
    
    # 4. RFM Summary data
    "rfm_summary.json": """
        SELECT 
            rfm_segment,
            customer_count,
            customer_share_pct,
            total_revenue,
            revenue_share_pct,
            aov
        FROM (
            SELECT 
                rfm_segment,
                COUNT(*) as customer_count,
                ROUND((COUNT(*)::numeric / SUM(COUNT(*)) OVER ()) * 100, 2) as customer_share_pct,
                ROUND(SUM(raw_monetary), 2) as total_revenue,
                ROUND((SUM(raw_monetary) / SUM(SUM(raw_monetary)) OVER ()) * 100, 2) as revenue_share_pct,
                ROUND(AVG(raw_monetary), 2) as aov
            FROM view_rfm_segmentation
            GROUP BY rfm_segment
        ) t
        ORDER BY total_revenue DESC;
    """,
    
    # 5. Cohort retention data
    "cohort_retention.json": "SELECT * FROM view_cohort_retention ORDER BY cohort_month ASC, cohort_index ASC;",
    
    # 6. Delivery root cause analysis data
    "delivery_root_cause.json": "SELECT * FROM view_delivery_root_cause WHERE total_deliveries >= 100 ORDER BY late_delivery_rate_pct DESC;",
    
    # 7. Time patterns data
    "time_patterns.json": "SELECT * FROM view_time_patterns ORDER BY day_of_week ASC, hour_of_day ASC;",

    # 8. Geo & Category View data
    "geo_revenue.json": """
        -- State Revenue concentration
        SELECT 
            state,
            ROUND(SUM(total_payment), 2) as revenue,
            ROUND((SUM(total_payment) / (SELECT SUM(total_payment) FROM fact_orders WHERE order_status NOT IN ('canceled', 'unavailable'))) * 100, 2) as revenue_share_pct
        FROM fact_orders o
        INNER JOIN dim_customers c ON o.customer_unique_id = c.customer_unique_id
        WHERE order_status NOT IN ('canceled', 'unavailable')
        GROUP BY state
        ORDER BY revenue DESC
        LIMIT 10;
    """,
    "category_performance.json": """
        -- Category Revenue vs Review Score overlay
        WITH order_reviews AS (
            SELECT order_id, AVG(review_score::numeric) as avg_score
            FROM raw_order_reviews
            GROUP BY order_id
        )
        SELECT 
            p.category_english,
            ROUND(SUM(oi.price::numeric), 2) as revenue,
            ROUND(AVG(r.avg_score), 2) as avg_review_score,
            COUNT(DISTINCT o.order_id) as total_orders
        FROM fact_orders o
        INNER JOIN raw_order_items oi ON o.order_id = oi.order_id
        INNER JOIN dim_products p ON oi.product_id = p.product_id
        LEFT JOIN order_reviews r ON o.order_id = r.order_id
        WHERE o.order_status NOT IN ('canceled', 'unavailable')
        GROUP BY p.category_english
        ORDER BY revenue DESC
        LIMIT 15;
    """,
    "payment_trends.json": """
        -- Monthly payment method split
        SELECT 
            DATE_TRUNC('month', o.purchase_timestamp)::date as order_month,
            rp.payment_type,
            COUNT(*) as transaction_count,
            ROUND(SUM(rp.payment_value::numeric), 2) as payment_value
        FROM fact_orders o
        INNER JOIN raw_order_payments rp ON o.order_id = rp.order_id
        WHERE o.order_status NOT IN ('canceled', 'unavailable')
        GROUP BY 1, 2
        ORDER BY order_month ASC, payment_value DESC;
    """
}

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "dashboard", "data")

def export_to_json():
    conn = get_connection()
    cur = conn.cursor()
    
    # Ensure export directory exists
    os.makedirs(DATA_DIR, exist_ok=True)
    
    print("=" * 60)
    print("EXPORTING ANALYTICAL DATA TO JSON FOR DASHBOARDS")
    print("=" * 60)
    
    for filename, query in EXPORT_QUERIES.items():
        filepath = os.path.join(DATA_DIR, filename)
        
        cur.execute(query)
        
        # Get column names
        colnames = [desc[0] for desc in cur.description]
        
        # Fetch rows
        rows = cur.fetchall()
        
        # Convert rows to list of dictionaries
        data = []
        for row in rows:
            data.append(dict(zip(colnames, row)))
            
        # Write to JSON file
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, cls=DashboardJsonEncoder, indent=2)
            
        print(f"  ✅ Exported {filename:<25} → {len(data):>6,} records")
        
    cur.close()
    conn.close()
    print("=" * 60)
    print("  All data exported successfully to dashboard/data/")
    print("=" * 60)

if __name__ == "__main__":
    export_to_json()
