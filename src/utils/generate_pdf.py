import os
import sys

# Ensure fpdf2 can be imported; otherwise we instruct the user to run pip install
try:
    from fpdf import FPDF
except ImportError:
    print("Error: 'fpdf2' is not installed in the virtual environment. Please install it using: .venv/bin/pip install fpdf2")
    sys.exit(1)

class EcomReportPDF(FPDF):
    def header(self):
        if self.page_no() > 1:
            self.set_font('Helvetica', 'I', 8)
            self.set_text_color(100, 110, 120)
            self.cell(0, 10, 'E-Commerce Intelligence Platform: Technical Guide', 0, 0, 'L')
            self.cell(0, 10, 'Data Engineering & Machine Learning Case Study', 0, 1, 'R')
            # Thin separator line
            self.set_draw_color(220, 225, 230)
            self.set_line_width(0.5)
            self.line(10, self.get_y() + 1, 200, self.get_y() + 1)
            self.ln(10)

    def footer(self):
        self.set_y(-15)
        # Thin separator line above footer
        self.set_draw_color(220, 225, 230)
        self.set_line_width(0.5)
        self.line(10, self.get_y() - 1, 200, self.get_y() - 1)
        
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(100, 110, 120)
        self.cell(0, 10, 'Instacart Market Basket Case Study - Page ' + str(self.page_no()), 0, 0, 'C')

    def add_title_section(self, title):
        self.ln(5)
        self.set_font('Helvetica', 'B', 14)
        self.set_text_color(26, 82, 118)  # Professional steel blue
        self.cell(0, 10, title, 0, 1, 'L')
        self.ln(3)

    def add_subtitle_section(self, subtitle):
        self.set_font('Helvetica', 'B', 11)
        self.set_text_color(44, 62, 80)   # Dark slate
        self.cell(0, 8, subtitle, 0, 1, 'L')
        self.ln(2)

    def add_body_text(self, text):
        self.set_font('Helvetica', '', 10)
        self.set_text_color(51, 51, 51)    # Off-black
        self.multi_cell(0, 6, text)
        self.ln(4)

    def add_bullet_point(self, title, description):
        self.set_font('Helvetica', 'B', 10)
        self.set_text_color(44, 62, 80)
        self.write(6, " *  " + title + ": ")
        self.set_font('Helvetica', '', 10)
        self.set_text_color(51, 51, 51)
        self.write(6, description + "\n")
        self.ln(2)

    def add_code_block(self, code_text):
        self.set_fill_color(245, 247, 248) # Light grey background
        self.set_text_color(44, 62, 80)     # Monospaced color
        self.set_font('Courier', '', 9)
        self.multi_cell(0, 5, code_text, border=1, fill=True)
        self.ln(4)

def build_pdf():
    pdf = EcomReportPDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(15, 20, 15)
    pdf.alias_nb_pages()
    
    # =========================================================================
    # COVER PAGE
    # =========================================================================
    pdf.add_page()
    
    # Large Decorative Blue Bar on the Left
    pdf.set_fill_color(26, 82, 118)
    pdf.rect(0, 0, 10, 297, "F")
    
    # Title Block
    pdf.ln(40)
    pdf.set_font('Helvetica', 'B', 24)
    pdf.set_text_color(26, 82, 118)
    pdf.cell(0, 15, 'E-COMMERCE INTELLIGENCE', 0, 1, 'L')
    pdf.cell(0, 15, 'PLATFORM', 0, 1, 'L')
    
    # Subtitle
    pdf.ln(10)
    pdf.set_font('Helvetica', 'B', 13)
    pdf.set_text_color(100, 110, 120)
    pdf.cell(0, 8, 'A Comprehensive Guide to Analytics Engineering & Machine Learning', 0, 1, 'L')
    pdf.set_font('Helvetica', '', 11)
    pdf.cell(0, 8, 'Case Study: Ingesting and Mining 33.8 Million Instacart Transactions', 0, 1, 'L')
    
    # Divider line
    pdf.ln(15)
    pdf.set_draw_color(26, 82, 118)
    pdf.set_line_width(1)
    pdf.line(15, pdf.get_y(), 100, pdf.get_y())
    
    # Metadata Block
    pdf.ln(60)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(44, 62, 80)
    pdf.cell(0, 6, 'Target Competencies Developed:', 0, 1, 'L')
    
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(70, 80, 90)
    pdf.cell(0, 6, ' - Analytics Engineering & Dimensional Star Schema Modeling (DuckDB / SQL)', 0, 1, 'L')
    pdf.cell(0, 6, ' - High-Performance Vectorized ETL Pipelines (Polars / Parquet)', 0, 1, 'L')
    pdf.cell(0, 6, ' - Data-Driven Customer Clustered RFM Segmentations (Scikit-Learn K-Means)', 0, 1, 'L')
    pdf.cell(0, 6, ' - Machine Learning forecasting, Association Basket Rules, & Collaborative Recommenders', 0, 1, 'L')
    
    # Date & Author Info
    pdf.ln(40)
    pdf.set_font('Helvetica', 'I', 9)
    pdf.set_text_color(128, 128, 128)
    pdf.cell(0, 6, 'Date: June 2026', 0, 1, 'L')
    pdf.cell(0, 6, 'Platform Version: 1.0 (Production-Grade Fallback Active)', 0, 1, 'L')
    
    # =========================================================================
    # PAGE 2: MEDALLION ARCHITECTURE
    # =========================================================================
    pdf.add_page()
    
    pdf.add_title_section('1. Medallion Data Architecture (Bronze -> Silver -> Gold)')
    
    pdf.add_body_text(
        "To manage and clean the 33.8 million transaction lines, the platform utilizes a "
        "Medallion Architecture. This design divides the analytical pipeline into progressive "
        "quality tiers to build a reliable data product."
    )
    
    pdf.add_subtitle_section('Bronze Layer: Ingestion & Serialization')
    pdf.add_bullet_point(
        "Ingestion Source",
        "Copies raw CSV datasets (700MB uncompressed) from the local archive folder."
    )
    pdf.add_bullet_point(
        "Parquet Conversion",
        "Converts rows to Snappy-compressed Parquet files, reducing space on disk to under 150MB."
    )
    pdf.add_bullet_point(
        "Why Parquet over CSV?",
        "CSVs are row-oriented and stored as text. Parquet is columnar (allowing fast column-only reads) and typed, saving disk size and memory when querying millions of items."
    )
    pdf.add_bullet_point(
        "Polars vs. Pandas",
        "Pandas runs on a single thread and creates massive overhead. Polars is built in Rust and uses all CPU cores concurrently to stream data in parallel."
    )
    
    pdf.add_subtitle_section('Silver Layer: Cleaning & Schema Validation')
    pdf.add_bullet_point(
        "Data Hygiene",
        "Enforces database column types, handles null values (setting first order days-since-prior to 0), and screens for negative metrics."
    )
    pdf.add_bullet_point(
        "Temporal Calibration",
        "Since the raw Instacart data lacks absolute calendar timestamps, we anchored each user's starting point to 2025 and added cumulative days per order to build a realistic calendar timeline."
    )
    
    pdf.add_subtitle_section('Gold Layer: Star Schema Modeling')
    pdf.add_body_text(
        "In the final layer, cleaned files are loaded into a localized DuckDB relational database, "
        "organizing them into a structured Star Schema optimized for downstream querying and BI dashboarding."
    )
    
    # =========================================================================
    # PAGE 3: STAR SCHEMA & DUCKDB
    # =========================================================================
    pdf.add_page()
    
    pdf.add_title_section('2. Dimensional Modeling & Star Schema')
    
    pdf.add_body_text(
        "For the database, we modeled the relations as a Star Schema. Fact tables capture "
        "numerical metrics, and Dimension tables capture descriptive contexts. This layout "
        "optimizes search performance and reduces duplication."
    )
    
    pdf.add_bullet_point(
        "FactOrders (Fact Table)",
        "Holds the numeric transactions of every items. Fields: order_id, user_id (FK), product_id (FK), date_key (FK), add_to_cart_order, quantity (1), unit_price, subtotal."
    )
    pdf.add_bullet_point(
        "DimCustomers (Dimension)",
        "Customer lifetime details. Fields: user_id, first_order_date, total_orders, total_spend, rfm_segment, clv, kmeans_segment."
    )
    pdf.add_bullet_point(
        "DimProducts (Dimension)",
        "Items inventory catalog. Fields: product_id, product_name, aisle_id (FK), department_id (FK), unit_price, abc_class."
    )
    pdf.add_bullet_point(
        "DimDate (Dimension)",
        "Temporal calendar granularity at the date-hour key (YYYYMMDDHH) level. Fields: date_key, date, day_of_week, hour_of_day, month, year."
    )
    
    pdf.add_subtitle_section('DuckDB: The Analytical Database Engine')
    pdf.add_body_text(
        "SQLite is a row-oriented transactional (OLTP) engine meant for simple lookups. "
        "In contrast, DuckDB is a vectorized, columnar engine designed for analytical (OLAP) queries. "
        "It stores columns contiguously in memory and processes vector arrays of values. This allows "
        "DuckDB to compute sums, averages, and group-bys on 33.8 million rows in milliseconds."
    )
    
    pdf.add_subtitle_section('Performance Indexing')
    pdf.add_body_text(
        "We created indexes on foreign key dimensions (user_id, product_id, date_key) inside the "
        "fact_orders table. When joining tables, DuckDB references these pre-sorted indexes, "
        "avoiding full table scans."
    )
    
    # =========================================================================
    # PAGE 4: SEMANTIC LAYER & CUSTOMER SEGMENTATION
    # =========================================================================
    pdf.add_page()
    
    pdf.add_title_section('3. Semantic KPI Views')
    pdf.add_body_text(
        "To abstract complexity, we built a Semantic Layer using SQL Views inside DuckDB. "
        "A SQL View is a stored query rather than a physical table. Whenever a view is queried, "
        "DuckDB dynamically computes the aggregation. This ensures that the Streamlit app always pulls "
        "consistent, real-time calculations directly from the warehouse."
    )
    pdf.add_bullet_point(
        "v_executive_kpis",
        "Calculates baseline KPIs: Total Revenue, Total Orders, Average Order Value (AOV), Active Customers, and Repeat Purchase Rate."
    )
    pdf.add_bullet_point(
        "v_product_performance",
        "Calculates total sales counts and compiles Pareto cumulative revenues to categorize inventory classes."
    )
    
    pdf.add_title_section('4. Customer Segmentation (RFM + K-Means)')
    
    pdf.add_subtitle_section('Rule-Based RFM Metrics')
    pdf.add_body_text(
        "Customers are scored on a 1-5 scale across: Recency (days since last order), Frequency "
        "(total orders), and Monetary value (total spent). High-performing scoring yields segments "
        "like 'Champions' (high recency/frequency/monetary) and 'At Risk' (historically valuable but inactive)."
    )
    
    pdf.add_subtitle_section('Data-Driven K-Means Clustering')
    pdf.add_body_text(
        "To identify customer groupings mathematically, we train a K-Means algorithm:"
    )
    pdf.add_bullet_point(
        "Log Transform",
        "RFM values are heavily skewed (a few shoppers spend thousands while most spend under $100). Log scaling (np.log1p) normalizes right-skewed tails."
    )
    pdf.add_bullet_point(
        "StandardScaler",
        "Since K-Means relies on distance calculations, we standardize values. This prevents Monetary (dollars) from dominating Recency (days) in scaling."
    )
    pdf.add_bullet_point(
        "Cluster Profiling",
        "The model forms 4 segments, which we automatically label based on their relative spend and frequency averages: 'VIPs', 'At Risk', 'Lost', and 'New Customers'."
    )
    
    # =========================================================================
    # PAGE 5: FORECASTING & ANOMALIES
    # =========================================================================
    pdf.add_page()
    
    pdf.add_title_section('5. Daily Demand Forecasting')
    pdf.add_body_text(
        "To optimize inventory planning, we forecast future revenue using statistical time-series "
        "and machine learning regressor models."
    )
    
    pdf.add_subtitle_section('Holt-Winters Exponential Smoothing')
    pdf.add_body_text(
        "Holt-Winters models baseline, trend, and weekly cycles. In simulated datasets, timelines "
        "gradually tail off. If we use a standard linear trend, it projects revenue downward to infinity. "
        "We configured a Damped Trend (damped_trend=True) and clipped future values (np.clip(..., 0, None)) "
        "to ensure forecasts stabilize realistically at a non-negative baseline."
    )
    
    pdf.add_subtitle_section('RandomForest Regressor (XGBoost Fallback)')
    pdf.add_body_text(
        "Machine learning models cannot predict time-series without feature engineering. We create:"
    )
    pdf.add_bullet_point(
        "Lag Features",
        "Sales from yesterday (lag_1), a week ago (lag_7), and two weeks ago (lag_14) to capture baseline offsets."
    )
    pdf.add_bullet_point(
        "Rolling Windows",
        "7-day and 30-day rolling averages to capture medium-term business momentum."
    )
    pdf.add_bullet_point(
        "Cross-Platform Fallback",
        "XGBoost requires compilation libraries (OpenMP) missing by default on macOS. We catch load errors and automatically substitute Scikit-learn's RandomForestRegressor, yielding robust execution."
    )
    
    pdf.add_title_section('6. Transaction Anomaly Detection')
    pdf.add_body_text(
        "We use an Isolation Forest algorithm on daily order count and revenue. It isolates outliers "
        "by building tree partitions. Normal days require many splits to isolate, while anomalous days "
        "(extreme peak sales or drop-offs) require very few splits. We configured a contamination rate of "
        "1% (contamination=0.01) to flag the top operational anomalies in the history."
    )
    
    # =========================================================================
    # PAGE 6: RECOMMENDATION SYSTEMS
    # =========================================================================
    pdf.add_page()
    
    pdf.add_title_section('7. Product Recommendation Systems')
    pdf.add_body_text(
        "The platform utilizes two recommendation frameworks to personalize checkout experiences and "
        "drive average order value."
    )
    
    pdf.add_subtitle_section('Market Basket Analysis (MBA)')
    pdf.add_body_text(
        "Mines co-purchase relationships inside transaction carts based on association rules:"
    )
    pdf.add_bullet_point(
        "Support",
        "The fraction of total orders containing both Product A and Product B."
    )
    pdf.add_bullet_point(
        "Confidence",
        "The conditional probability that a customer buys Product B given they have placed Product A in their cart."
    )
    pdf.add_bullet_point(
        "Lift",
        "The ratio of observed joint purchase to independent probability. Lift > 1 indicates that A and B are bought together far more frequently than by random chance."
    )
    pdf.add_body_text(
        "We executed a high-performance Polars self-join on 22.3 million row item combinations, "
        "mining rules (e.g. Fuji Apples + Organic Strawberries has a 67.0x Lift)."
    )
    
    pdf.add_subtitle_section('Item-Item Collaborative Filtering')
    pdf.add_body_text(
        "Pre-computes personalized suggestions for customers who have historical order patterns:"
    )
    pdf.add_bullet_point(
        "Sparse Matrix",
        "Constructs a scipy sparse category matrix of user-product purchase counts, saving memory."
    )
    pdf.add_bullet_point(
        "Cosine Similarity",
        "Computes similarity angles between product columns to build co-occurrence similarity maps."
    )
    pdf.add_bullet_point(
        "Scoring",
        "Recommends candidate items by multiplying a user's purchase counts against the item-to-item similarity matrix (filtering out already purchased items)."
    )
    
    # =========================================================================
    # PAGE 7: BUSINESS SUMMARY & SOLUTIONS
    # =========================================================================
    pdf.add_page()
    
    pdf.add_title_section('8. Executive Insights & Decision Frameworks')
    pdf.add_body_text(
        "To ensure the system is valuable out-of-the-box, we compiled a rich, deterministic executive report "
        "that executes queries on Gold semantic views. Here are the core insights and operational actions:"
    )
    pdf.add_bullet_point(
        "Customer Pareto Split",
        "The Champions RFM segment contributes 62.9% of total revenue while representing only 26.5% of the customer base, proving the 80/20 rule. Action: Prioritize VIP retention campaigns."
    )
    pdf.add_bullet_point(
        "Inventory ABC Split",
        "Class A products constitute 9.8% of the catalog but drive 80.0% of total revenue. Class C is 68.7% of the catalog driving just 5.0% of sales. Action: Focus quality checks on Class A, and move Class C to just-in-time logistics."
    )
    pdf.add_bullet_point(
        "Logistics Peak Windows",
        "Peak transactions occur on Wednesday at 11:00. Action: Staff logistics 2 hours ahead of this peak window."
    )
    
    pdf.add_title_section('9. Production Best Practices (Do\'s & Don\'ts)')
    
    pdf.add_subtitle_section('What to Do')
    pdf.add_bullet_point(
        "Use Vectorized ETL",
        "Always use multi-threaded columnar frameworks (Polars/Parquet) when processing datasets over 10M rows to avoid memory overhead."
    )
    pdf.add_bullet_point(
        "Damp Trends",
        "Always damp and clip forecasting trends on finite/staggered simulations so they don't project unrealistic values."
    )
    pdf.add_bullet_point(
        "Indexes",
        "Create primary/foreign key indexes on analytical tables (DuckDB) to speed up transactional join queries."
    )
    
    pdf.add_subtitle_section('What Not to Do')
    pdf.add_bullet_point(
        "Don't Loop",
        "Never use Python loops (for-loops) to clean or transform data rows. Vectorized operations run 100x faster."
    )
    pdf.add_bullet_point(
        "Don't use CSV for OLAP",
        "Never query raw text CSVs inside dashboard loops. Load tables into an indexed database (DuckDB)."
    )
    
    # Save PDF
    output_path = "comprehensive_project_guide.pdf"
    pdf.output(output_path)
    print(f"PDF successfully built and saved to: {output_path}")

if __name__ == "__main__":
    build_pdf()
