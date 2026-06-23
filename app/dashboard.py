import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import yaml

st.set_page_config(
    page_title="E-Commerce Intelligence Platform",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# PREMIUM DESIGN SYSTEM & CUSTOM CSS
# ==============================================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Deep Navy Gradient Background */
    .stApp {
        background: linear-gradient(135deg, #0a0e27 0%, #1a1a3e 100%);
        color: #e2e8f0;
    }
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: rgba(15, 23, 42, 0.6);
        backdrop-filter: blur(12px);
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    /* Glassmorphism Cards for Metrics */
    div[data-testid="metric-container"] {
        background: rgba(30, 41, 59, 0.5);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 20px;
        border-radius: 16px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    
    div[data-testid="metric-container"]:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 40px 0 rgba(99, 102, 241, 0.3);
        border: 1px solid rgba(99, 102, 241, 0.5);
    }
    
    /* Metric Value Styling */
    div[data-testid="metric-container"] > div:nth-child(1) {
        color: #94a3b8; /* Label */
        font-weight: 500;
        font-size: 0.95rem;
    }
    div[data-testid="metric-container"] > div:nth-child(2) {
        color: #ffffff; /* Value */
        font-weight: 700;
        font-size: 2rem;
        background: -webkit-linear-gradient(45deg, #60a5fa, #a78bfa);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        background-color: rgba(15, 23, 42, 0.4);
        border-radius: 12px;
        padding: 4px;
        gap: 8px;
        border: 1px solid rgba(255, 255, 255, 0.05);
    }
    .stTabs [data-baseweb="tab"] {
        height: 46px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 8px;
        color: #94a3b8;
        font-weight: 500;
        border: none;
        transition: all 0.2s ease;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: #f8fafc;
        background-color: rgba(255, 255, 255, 0.05);
    }
    .stTabs [aria-selected="true"] {
        background-color: rgba(99, 102, 241, 0.2) !important;
        color: #818cf8 !important;
        border: 1px solid rgba(99, 102, 241, 0.4) !important;
        box-shadow: 0 0 15px rgba(99, 102, 241, 0.2);
    }
    
    /* Dataframes/Tables Glass Effect */
    [data-testid="stDataFrame"] {
        background: rgba(30, 41, 59, 0.4);
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.05);
        padding: 10px;
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #f8fafc;
        font-weight: 600;
    }
    
    hr {
        border-color: rgba(255,255,255,0.1);
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# DATA LOADING & CACHING
# ==============================================================================
@st.cache_resource
def get_db_connection():
    config_path = "configs/pipeline_config.yaml"
    db_path = "data/gold/ecommerce_analytics.db"
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        db_path = config["paths"].get("gold_db_path", db_path)
        
    if os.path.exists(db_path):
        return duckdb.connect(db_path, read_only=True)
    return None

conn = get_db_connection()

@st.cache_data(ttl=3600)
def load_data(query, table_name=None):
    """
    Executes a SQL query against DuckDB. If DuckDB is missing (e.g. Streamlit Cloud),
    it reads from the static Parquet cache instead.
    """
    if conn is not None:
        try:
            return conn.execute(query).df()
        except Exception as e:
            st.error(f"Query failed: {e}")
            return pd.DataFrame()
    else:
        # Fallback to Parquet cache
        if not table_name:
            # Try to extract table name from simple SELECT * FROM table_name queries
            import re
            match = re.search(r'FROM\s+([a-zA-Z0-9_]+)', query, re.IGNORECASE)
            if match:
                table_name = match.group(1)
        
        if table_name:
            cache_file = f"data/dashboard_cache/{table_name}.parquet"
            if os.path.exists(cache_file):
                df = pd.read_parquet(cache_file)
                # Handle simple WHERE filters if present in the query string
                if "WHERE department = " in query:
                    dept = query.split("WHERE department = '")[1].split("'")[0]
                    if "department" in df.columns:
                        df = df[df["department"] == dept]
                
                # Handle ORDER BY and LIMIT if present
                if "ORDER BY" in query:
                    order_col = query.split("ORDER BY ")[1].split()[0]
                    ascending = "DESC" not in query.upper()
                    if order_col in df.columns:
                        df = df.sort_values(by=order_col, ascending=ascending)
                
                if "LIMIT" in query:
                    try:
                        limit_val = int(query.split("LIMIT ")[1].split()[0])
                        df = df.head(limit_val)
                    except:
                        pass
                
                return df
                
        st.error("Database connection missing and cache not found.")
        return pd.DataFrame()

# ==============================================================================
# SIDEBAR INFO
# ==============================================================================
st.sidebar.markdown("### ℹ️ About Platform")
st.sidebar.info(
    "Enterprise E-Commerce Intelligence Portal.\n\n"
    "Powered by: **DuckDB** + **Polars**\n\n"
    "Data size: **33.8M rows**\n\n"
    "DQ Score: **100%**"
)

# ==============================================================================
# MAIN DASHBOARD HEADER
# ==============================================================================
st.markdown("<h1 style='text-align: center; margin-bottom: 30px; background: -webkit-linear-gradient(45deg, #60a5fa, #c084fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>🔮 Intelligence Command Center</h1>", unsafe_allow_html=True)

# Define Tabs
tab_exec, tab_cust, tab_prod, tab_basket, tab_forecast, tab_dq = st.tabs([
    "📊 Executive Summary", 
    "👥 Customer Intelligence", 
    "📦 Product Analytics", 
    "🛒 Basket Intelligence",
    "📈 Demand Forecasting",
    "🔍 Data Quality"
])

# Standard Plotly layout template
plotly_layout = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter", color="#cbd5e0"),
    margin=dict(l=20, r=20, t=40, b=20)
)

# ==============================================================================
# TAB 1: EXECUTIVE SUMMARY
# ==============================================================================
with tab_exec:
    # 1. Monthly KPIs
    monthly_kpis = load_data("SELECT * FROM v_monthly_kpis ORDER BY month DESC LIMIT 2")
    if not monthly_kpis.empty and len(monthly_kpis) >= 2:
        current = monthly_kpis.iloc[0]
        st.markdown("### 📌 Key Performance Indicators (Latest Month)")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Monthly Revenue", f"${current['revenue']:,.0f}", f"{current['revenue_growth_pct']}% MoM")
        c2.metric("Monthly Orders", f"{int(current['orders']):,}", f"{current['order_growth_pct']}% MoM")
        c3.metric("Avg Order Value", f"${current['avg_order_value']:.2f}")
        c4.metric("New Customers", f"{int(current['new_customers']):,}")
        st.markdown("<br>", unsafe_allow_html=True)
    
    # 2. Revenue Trend & Anomalies
    st.markdown("### 📈 Daily Revenue Tracking & Anomaly Detection")
    anomalies_df = load_data("SELECT date, revenue, is_anomaly FROM daily_anomalies ORDER BY date")
    if not anomalies_df.empty:
        anomalies_df["date"] = pd.to_datetime(anomalies_df["date"])
        fig_sales = go.Figure()
        
        # Area fill for revenue
        fig_sales.add_trace(go.Scatter(
            x=anomalies_df["date"], y=anomalies_df["revenue"],
            mode="lines", line=dict(color="#6366f1", width=2),
            fill="tozeroy", fillcolor="rgba(99, 102, 241, 0.1)",
            name="Revenue"
        ))
        
        # Anomalies
        anoms = anomalies_df[anomalies_df["is_anomaly"] == 1]
        if not anoms.empty:
            fig_sales.add_trace(go.Scatter(
                x=anoms["date"], y=anoms["revenue"],
                mode="markers", marker=dict(color="#f43f5e", size=10, symbol="circle", line=dict(color="white", width=1)),
                name="Anomaly Detected"
            ))
            
        fig_sales.update_layout(**plotly_layout, hovermode="x unified", height=350)
        st.plotly_chart(fig_sales, use_container_width=True)

    # 3. AI Insights Panel
    st.markdown("### 🤖 GenAI Strategy Insights")
    insights_path = "data/gold/ai_insights.md"
    if os.path.exists(insights_path):
        with open(insights_path, "r") as f:
            insights_md = f.read()
        st.markdown(f"<div style='background: rgba(16, 185, 129, 0.05); border-left: 4px solid #10b981; padding: 20px; border-radius: 0 8px 8px 0;'>{insights_md}</div>", unsafe_allow_html=True)

# ==============================================================================
# TAB 2: CUSTOMER INTELLIGENCE
# ==============================================================================
with tab_cust:
    st.markdown("### 🔥 Monthly Cohort Retention Matrix")
    cohort_df = load_data("SELECT cohort_month, month_number, retention_rate_pct FROM v_cohort_retention WHERE month_number > 0 AND cohort_month >= '2025-01-01'")
    if not cohort_df.empty:
        cohort_df["cohort_month"] = pd.to_datetime(cohort_df["cohort_month"]).dt.strftime('%Y-%m')
        cohort_pivot = cohort_df.pivot(index="cohort_month", columns="month_number", values="retention_rate_pct")
        
        fig_cohort = px.imshow(
            cohort_pivot, 
            text_auto=".1f", 
            aspect="auto",
            color_continuous_scale=[[0, '#0f172a'], [0.5, '#3b82f6'], [1, '#10b981']],
            labels=dict(x="Months Since First Purchase", y="Cohort Month", color="Retention %")
        )
        fig_cohort.update_layout(**plotly_layout, height=400)
        st.plotly_chart(fig_cohort, use_container_width=True)

    c1, c2 = st.columns(2)
    
    with c1:
        st.markdown("### 💎 RFM Revenue Matrix")
        rfm_matrix = load_data("SELECT r_score, f_score, avg_monetary FROM v_rfm_revenue_matrix")
        if not rfm_matrix.empty:
            rfm_pivot = rfm_matrix.pivot(index="r_score", columns="f_score", values="avg_monetary")
            fig_rfm = px.imshow(
                rfm_pivot, text_auto=".0f", 
                color_continuous_scale="Purp", origin="lower",
                labels=dict(x="Frequency Score (High is better)", y="Recency Score (High is better)", color="Avg Spend $")
            )
            fig_rfm.update_layout(**plotly_layout, height=350)
            st.plotly_chart(fig_rfm, use_container_width=True)

    with c2:
        st.markdown("### 🏆 Customer Lifetime Value (CLV) Tiers")
        clv_df = load_data("SELECT * FROM v_customer_ltv", table_name="v_customer_ltv")
        if not clv_df.empty:
            clv_df = clv_df.groupby("clv_tier")["projected_annual_clv"].sum().reset_index(name="total_value")
            fig_clv = px.pie(
                clv_df, values="total_value", names="clv_tier", hole=0.6, 
                color_discrete_sequence=["#f59e0b", "#6366f1", "#10b981", "#64748b"]
            )
            fig_clv.update_traces(textposition='inside', textinfo='percent+label')
            fig_clv.update_layout(**plotly_layout, height=350, showlegend=False, 
                                  annotations=[dict(text='CLV', x=0.5, y=0.5, font_size=20, showarrow=False)])
            st.plotly_chart(fig_clv, use_container_width=True)
            
    c3, c4 = st.columns(2)
    with c3:
        st.markdown("### 📊 Customer Segment Migration (Summary)")
        segment_summary_df = load_data("SELECT * FROM v_segment_summary ORDER BY avg_spend DESC")
        if not segment_summary_df.empty:
            st.dataframe(segment_summary_df[['rfm_segment', 'customers', 'pct_of_total', 'avg_spend', 'revenue_share_pct']], use_container_width=True)

    with c4:
        st.markdown("### 🛒 Purchase Frequency Distribution")
        frequency_df = load_data("SELECT frequency_bucket, customer_count, revenue_pct FROM v_purchase_frequency")
        if not frequency_df.empty:
            fig_freq = px.bar(
                frequency_df, x="customer_count", y="frequency_bucket", orientation='h',
                color="revenue_pct", color_continuous_scale="Viridis",
                labels={"customer_count": "Number of Customers", "frequency_bucket": "Frequency Bucket", "revenue_pct": "Revenue %"}
            )
            fig_freq.update_layout(**plotly_layout, height=300, showlegend=False, yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_freq, use_container_width=True)


# ==============================================================================
# TAB 3: PRODUCT ANALYTICS
# ==============================================================================
with tab_prod:
    # Local Tab Filters
    dept_df = load_data("SELECT department FROM dim_departments ORDER BY department", table_name="dim_departments")
    departments = ["All"] + dept_df["department"].tolist() if not dept_df.empty else ["All"]
    
    col_filter, _ = st.columns([1, 3])
    with col_filter:
        selected_dept = st.selectbox("🎛️ Filter by Department:", departments)
        
    dept_filter = ""
    if selected_dept != "All":
        dept_filter = f"WHERE department = '{selected_dept}'"

    st.markdown("### 📈 Revenue Concentration (Pareto Curve)")
    pareto_df = load_data(f"SELECT revenue_rank, cumulative_revenue_pct FROM v_revenue_concentration {dept_filter} ORDER BY revenue_rank LIMIT 1000", table_name="v_revenue_concentration")
    if not pareto_df.empty:
        fig_pareto = px.line(
            pareto_df, x="revenue_rank", y="cumulative_revenue_pct", 
            labels={"revenue_rank": "Product Rank", "cumulative_revenue_pct": "Cumulative Revenue %"}
        )
        fig_pareto.add_hline(y=80, line_dash="dash", line_color="#f59e0b", annotation_text="80% Revenue")
        fig_pareto.update_traces(line=dict(color="#10b981", width=3))
        fig_pareto.update_layout(**plotly_layout, height=350)
        st.plotly_chart(fig_pareto, use_container_width=True)

    c1, c2 = st.columns(2)
    
    with c1:
        st.markdown("### 🎯 Department Penetration")
        pen_df = load_data("SELECT department, penetration_pct FROM v_department_penetration ORDER BY penetration_pct DESC LIMIT 10", table_name="v_department_penetration")
        if not pen_df.empty:
            fig_pen = px.bar(
                pen_df, x="penetration_pct", y="department", orientation='h',
                color="penetration_pct", color_continuous_scale="Blues",
                labels={"penetration_pct": "Penetration %", "department": "Department"}
            )
            fig_pen.update_layout(**plotly_layout, height=400, yaxis={'categoryorder':'total ascending'}, showlegend=False)
            st.plotly_chart(fig_pen, use_container_width=True)

    with c2:
        st.markdown("### 🔄 Reorder Behavior")
        reorder_df = load_data(f"SELECT department, reorder_rate_pct FROM v_reorder_behavior {dept_filter} ORDER BY reorder_rate_pct DESC LIMIT 50", table_name="v_reorder_behavior")
        if not reorder_df.empty:
            reorder_df = reorder_df.drop_duplicates(subset=["department"]).head(10)
            fig_reo = px.bar(
                reorder_df, x="department", y="reorder_rate_pct",
                color="reorder_rate_pct", color_continuous_scale="Emrld",
                labels={"reorder_rate_pct": "Reorder Rate %", "department": "Department"}
            )
            fig_reo.update_layout(**plotly_layout, height=400, showlegend=False)
            st.plotly_chart(fig_reo, use_container_width=True)
            
    st.markdown("### 🚀 Top Growing & Declining Products (MoM)")
    trends_df = load_data(f"""
        SELECT month, product_name, department, revenue, revenue_growth_pct 
        FROM v_product_trends 
        {dept_filter}
        ORDER BY month DESC, ABS(revenue_growth_pct) DESC 
        LIMIT 15
    """, table_name="v_product_trends")
    if not trends_df.empty:
        st.dataframe(trends_df, use_container_width=True)

# ==============================================================================
# TAB 4: BASKET INTELLIGENCE
# ==============================================================================
with tab_basket:
    c1, c2 = st.columns([1.5, 1])
    
    with c1:
        st.markdown("### 📦 Cart Size Distribution")
        cart_df = load_data("SELECT cart_size_bucket, order_count, avg_cart_value FROM v_cart_analysis ORDER BY min_items")
        if not cart_df.empty:
            fig_cart = px.bar(
                cart_df, x="cart_size_bucket", y="order_count", 
                text="avg_cart_value", color="avg_cart_value", color_continuous_scale="Purp",
                labels={"cart_size_bucket": "Items in Cart", "order_count": "Number of Orders", "avg_cart_value": "Avg Value"}
            )
            fig_cart.update_traces(texttemplate='$%{text:.2f}', textposition='outside')
            fig_cart.update_layout(**plotly_layout, height=400, showlegend=False)
            st.plotly_chart(fig_cart, use_container_width=True)
            
    with c2:
        st.markdown("### 🕰️ Purchase Time Heatmap")
        heatmap_df = load_data("SELECT day_name, hour_of_day, order_count FROM v_day_hour_heatmap")
        if not heatmap_df.empty:
            day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            heat_pivot = heatmap_df.pivot(index="day_name", columns="hour_of_day", values="order_count").reindex(day_order)
            fig_heat = px.imshow(
                heat_pivot, aspect="auto", color_continuous_scale="Plasma",
                labels=dict(x="Hour of Day", y="Day of Week", color="Orders")
            )
            fig_heat.update_layout(**plotly_layout, height=400)
            st.plotly_chart(fig_heat, use_container_width=True)
            
    c3, c4 = st.columns(2)
    with c3:
        st.markdown("### 🛒 Association Rules (Market Basket Analysis)")
        assoc_df = load_data("""
            SELECT p1.product_name as "Product A", p2.product_name as "Product B", r.lift as "Lift", r.confidence_a_b as "Confidence A->B"
            FROM association_rules r JOIN dim_products p1 ON r.product_id_a = p1.product_id JOIN dim_products p2 ON r.product_id_b = p2.product_id
            ORDER BY r.lift DESC LIMIT 15
        """)
        if not assoc_df.empty:
            st.dataframe(assoc_df, use_container_width=True)
            
    with c4:
        st.markdown("### 🔗 Department Cross-Sell Matrix")
        cross_sell_df = load_data("""
            SELECT department_a, department_b, pct_of_a_also_buy_b 
            FROM v_department_cross_sell 
            ORDER BY pct_of_a_also_buy_b DESC LIMIT 15
        """)
        if not cross_sell_df.empty:
            st.dataframe(cross_sell_df, use_container_width=True)

# ==============================================================================
# TAB 5: DEMAND FORECASTING
# ==============================================================================
with tab_forecast:
    st.markdown("### 🔮 Advanced Demand Forecasting")
    
    history = load_data("SELECT date, actual_revenue, predicted_revenue_hw, predicted_revenue_xgb FROM forecast_evaluation ORDER BY date")
    forecast = load_data("SELECT forecast_date, predicted_revenue, model_used FROM forecast_predictions ORDER BY forecast_date")
    
    if not history.empty and not forecast.empty:
        history["date"] = pd.to_datetime(history["date"])
        forecast["forecast_date"] = pd.to_datetime(forecast["forecast_date"])
        
        fig_f = go.Figure()
        
        # History
        fig_f.add_trace(go.Scatter(x=history["date"], y=history["actual_revenue"], name="Actual Revenue", line=dict(color="#cbd5e0", width=2)))
        # XGB Fit
        fig_f.add_trace(go.Scatter(x=history["date"], y=history["predicted_revenue_xgb"], name="ML Fit (XGBoost)", line=dict(color="#f59e0b", dash="dot")))
        # HW Fit
        fig_f.add_trace(go.Scatter(x=history["date"], y=history["predicted_revenue_hw"], name="HW Fit", line=dict(color="#10b981", dash="dot")))
        # Future
        fig_f.add_trace(go.Scatter(x=forecast["forecast_date"], y=forecast["predicted_revenue"], name="Future Forecast", line=dict(color="#8b5cf6", width=3)))
        
        fig_f.update_layout(**plotly_layout, height=500, hovermode="x unified")
        st.plotly_chart(fig_f, use_container_width=True)

# ==============================================================================
# TAB 6: DATA QUALITY
# ==============================================================================
with tab_dq:
    st.markdown("### 🛡️ Enterprise Data Quality Report")
    
    dq_scores = load_data("SELECT * FROM dq_table_scores")
    if not dq_scores.empty:
        overall_score = dq_scores['overall_dq_score'].mean()
        
        # Display large Gauge chart
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = overall_score,
            title = {'text': "Overall Warehouse DQ Score", 'font': {'color': '#cbd5e0'}},
            gauge = {
                'axis': {'range': [None, 100], 'tickcolor': '#cbd5e0'},
                'bar': {'color': "#10b981"},
                'steps': [
                    {'range': [0, 70], 'color': "#ef4444"},
                    {'range': [70, 90], 'color': "#f59e0b"},
                    {'range': [90, 100], 'color': "rgba(16, 185, 129, 0.2)"}
                ]
            }
        ))
        fig_gauge.update_layout(**plotly_layout, height=300)
        
        c1, c2 = st.columns([1, 2])
        with c1:
            st.plotly_chart(fig_gauge, use_container_width=True)
            
        with c2:
            st.markdown("#### Per-Table DQ Breakdown")
            st.dataframe(dq_scores[['table_name', 'overall_dq_score', 'completeness_score', 'validity_score', 'consistency_score', 'passed_checks', 'failed_checks']], use_container_width=True)
    else:
        st.info("Data Quality framework tables not found. Run the DQ engine.")
