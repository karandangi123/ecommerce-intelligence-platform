import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import os

# Set page config
st.set_page_config(page_title="Olist Marketplace Intelligence", layout="wide", initial_sidebar_state="collapsed")

# Custom Premium CSS Injection
st.markdown("""
<style>
/* App background */
.stApp {
    background-color: #07090e;
}
/* General Text */
h1, h2, h3, h4, h5, h6, p, span {
    font-family: 'Outfit', sans-serif !important;
}
/* Metrics styling */
[data-testid="stMetricValue"] {
    font-size: 2.2rem;
    font-weight: 700;
    color: #f3f4f6;
}
[data-testid="stMetricLabel"] {
    color: #9ca3af !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-size: 0.85rem;
}
[data-testid="stMetricDelta"] {
    font-weight: 600;
}
/* Glassmorphism Cards */
[data-testid="metric-container"] {
    background: rgba(18, 24, 38, 0.85);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 16px;
    padding: 1.5rem;
    box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
[data-testid="metric-container"]:hover {
    transform: translateY(-4px);
    border-color: rgba(99, 102, 241, 0.25);
    box-shadow: 0 15px 35px -10px rgba(99, 102, 241, 0.2);
}
/* Tab Styling */
.stTabs [data-baseweb="tab-list"] {
    gap: 1rem;
}
.stTabs [data-baseweb="tab"] {
    background: rgba(18, 24, 38, 0.85);
    border-radius: 8px 8px 0px 0px;
    padding: 0.5rem 1rem;
    color: #9ca3af;
    font-weight: 600;
}
.stTabs [aria-selected="true"] {
    background-color: rgba(99, 102, 241, 0.1);
    color: #f3f4f6;
    border-bottom-color: #6366f1 !important;
}
</style>
""", unsafe_allow_html=True)

st.title("Olist Marketplace Intelligence Platform")

# Path to the exported JSON data
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard", "data")

@st.cache_data
def load_data(filename):
    filepath = os.path.join(DATA_DIR, filename)
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            data = json.load(f)
        return pd.DataFrame(data)
    else:
        st.error(f"Data file not found: {filename}. Please run export_data.py first.")
        return pd.DataFrame()

# Load all datasets
ceo_data = load_data("ceo_monthly.json")
ops_data = load_data("ops_monthly.json")
mkt_data = load_data("marketing_monthly.json")
rfm_data = load_data("rfm_summary.json")
cohort_data = load_data("cohort_retention.json")
root_cause = load_data("delivery_root_cause.json")
geo_data = load_data("geo_revenue.json")
cat_data = load_data("category_performance.json")
pay_data = load_data("payment_trends.json")

# Helper for standard formatting
def format_currency(val):
    if val >= 1000000:
        return f"R${val/1000000:.2f}M"
    elif val >= 1000:
        return f"R${val/1000:.1f}k"
    return f"R${val:,.0f}"

def format_num(val):
    if val >= 1000000:
        return f"{val/1000000:.2f}M"
    elif val >= 1000:
        return f"{val/1000:.1f}k"
    return f"{val:,.0f}"

# Premium Chart Theme Configuration
chart_layout = dict(
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    font=dict(color='#f3f4f6', family='Outfit, sans-serif'),
    margin=dict(l=0, r=0, t=30, b=0),
    xaxis=dict(showgrid=False, zeroline=False, linecolor='rgba(255,255,255,0.1)', tickfont=dict(color='#9ca3af')),
    yaxis=dict(showgrid=True, gridcolor='rgba(255, 255, 255, 0.05)', zeroline=False, tickfont=dict(color='#9ca3af')),
    legend=dict(font=dict(color='#9ca3af'))
)

# Create Tabs
tab_ceo, tab_ops, tab_mkt, tab_geo = st.tabs([
    "👔 CEO Strategy", 
    "🚚 Operations & Logistics", 
    "🎯 Marketing & Customers",
    "🌎 Geo & Categories"
])

# --- 1. CEO STRATEGY TAB ---
with tab_ceo:
    if not ceo_data.empty:
        # Sort data by month ascending
        ceo_data = ceo_data.sort_values("order_month").reset_index(drop=True)
        
        # We target Aug 2018 for "current" metrics (the last full reliable month in Olist dataset)
        aug_idx_list = ceo_data.index[ceo_data['order_month'] == '2018-08-01'].tolist()
        if aug_idx_list:
            active_idx = aug_idx_list[0]
        else:
            active_idx = len(ceo_data) - 2
            
        active_month = ceo_data.iloc[active_idx]
        prev_month = ceo_data.iloc[active_idx - 1]
        
        # Calculate Rolling 12 Months
        ltm_data = ceo_data.iloc[max(0, active_idx - 11):active_idx + 1]
        prev_ltm_data = ceo_data.iloc[max(0, active_idx - 12):active_idx]
        
        ltm_revenue = ltm_data['total_revenue'].sum()
        ltm_orders = ltm_data['total_orders'].sum()
        prev_ltm_revenue = prev_ltm_data['total_revenue'].sum()
        prev_ltm_orders = prev_ltm_data['total_orders'].sum()
        
        ltm_rev_growth = ((ltm_revenue - prev_ltm_revenue) / prev_ltm_revenue) * 100
        ltm_ord_growth = ((ltm_orders - prev_ltm_orders) / prev_ltm_orders) * 100
        
        # Display Metrics
        st.subheader("Executive Summary (Aug 2018)")
        col1, col2, col3, col4, col5 = st.columns(5)
        
        col1.metric("LTM Revenue", format_currency(ltm_revenue), f"{ltm_rev_growth:.1f}% MoM (LTM)")
        col2.metric("LTM Orders", format_num(ltm_orders), f"{ltm_ord_growth:.1f}% MoM (LTM)")
        col3.metric("Monthly Revenue", format_currency(active_month['total_revenue']), f"{active_month['mom_revenue_growth_pct']:.1f}% MoM")
        col4.metric("Monthly Orders", format_num(active_month['total_orders']), f"{active_month['mom_orders_growth_pct']:.1f}% MoM")
        
        # Calculate AOV
        aov = active_month['total_revenue'] / max(1, active_month['total_orders'])
        prev_aov = prev_month['total_revenue'] / max(1, prev_month['total_orders'])
        aov_growth = ((aov - prev_aov) / prev_aov) * 100 if prev_aov > 0 else 0
        col5.metric("Avg Order Value", f"R${aov:.2f}", f"{aov_growth:.1f}% MoM")
        
        # Trend Chart
        st.markdown("### Revenue & Orders Trend")
        filtered_ceo = ceo_data[(ceo_data['order_month'] >= '2017-01-01') & (ceo_data['order_month'] <= '2018-08-01')].copy()
        filtered_ceo['Month'] = pd.to_datetime(filtered_ceo['order_month']).dt.strftime('%Y-%m')
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=filtered_ceo['Month'], y=filtered_ceo['total_revenue'], name="Revenue", fill='tozeroy', marker_color='#6366f1'))
        fig.add_trace(go.Scatter(x=filtered_ceo['Month'], y=filtered_ceo['total_orders'], name="Orders", yaxis="y2", marker_color='#10b981'))
        
        fig.update_layout(**chart_layout)
        fig.update_layout(
            yaxis=dict(title="Revenue (BRL)", side="left", showgrid=True, gridcolor='rgba(255, 255, 255, 0.05)', zeroline=False, tickfont=dict(color='#9ca3af')),
            yaxis2=dict(title="Orders", side="right", overlaying="y", showgrid=False, zeroline=False, tickfont=dict(color='#9ca3af')),
            hovermode="x unified",
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)

# --- 2. OPERATIONS & LOGISTICS TAB ---
with tab_ops:
    if not ops_data.empty:
        ops_data = ops_data.sort_values("order_month").reset_index(drop=True)
        aug_idx_list = ops_data.index[ops_data['order_month'] == '2018-08-01'].tolist()
        active_idx = aug_idx_list[0] if aug_idx_list else len(ops_data) - 2
        
        active_ops = ops_data.iloc[active_idx]
        prev_ops = ops_data.iloc[active_idx - 1]
        
        st.subheader("Logistics Performance (Aug 2018)")
        col1, col2, col3 = st.columns(3)
        col1.metric("On-Time Delivery Rate", f"{active_ops['otd_pct']}%", f"{active_ops['otd_pct'] - prev_ops['otd_pct']:.1f}% MoM")
        col2.metric("Avg Delivery Days", f"{active_ops['avg_delivery_days']}", f"{active_ops['avg_delivery_days'] - prev_ops['avg_delivery_days']:.1f} days", delta_color="inverse")
        col3.metric("Late Delivery Rate", f"{active_ops['late_delivery_rate_pct']}%", f"{active_ops['late_delivery_rate_pct'] - prev_ops['late_delivery_rate_pct']:.1f}% MoM", delta_color="inverse")
        
        st.markdown("### SLA Trend (Target: 10 days)")
        filtered_ops = ops_data[(ops_data['order_month'] >= '2017-01-01') & (ops_data['order_month'] <= '2018-08-01')].copy()
        filtered_ops['Month'] = pd.to_datetime(filtered_ops['order_month']).dt.strftime('%Y-%m')
        
        fig_ops = go.Figure()
        fig_ops.add_trace(go.Scatter(x=filtered_ops['Month'], y=filtered_ops['avg_delivery_days'], name="Avg Delivery Days", marker_color='#f59e0b', mode='lines+markers'))
        fig_ops.add_trace(go.Scatter(x=filtered_ops['Month'], y=[10]*len(filtered_ops), name="SLA Limit", line=dict(color='red', dash='dash')))
        fig_ops.update_layout(**chart_layout)
        fig_ops.update_layout(hovermode="x unified", height=300)
        st.plotly_chart(fig_ops, use_container_width=True)
        
        if not root_cause.empty:
            st.markdown("### Late Delivery Root Cause By Route")
            top_routes = root_cause.head(8).copy()
            top_routes['Route'] = top_routes['seller_state'] + " ➔ " + top_routes['customer_state']
            
            fig_rc = px.bar(top_routes, x="Route", y=["seller_fault_share_pct", "carrier_fault_share_pct"], 
                            title="Seller vs Carrier Fault Share", 
                            labels={"value": "Percentage (%)", "variable": "Fault Source"},
                            color_discrete_map={"seller_fault_share_pct": "#6366f1", "carrier_fault_share_pct": "#10b981"})
            fig_rc.update_layout(**chart_layout)
            fig_rc.update_layout(barmode="stack", height=350)
            st.plotly_chart(fig_rc, use_container_width=True)

# --- 3. MARKETING & CUSTOMERS TAB ---
with tab_mkt:
    if not mkt_data.empty:
        mkt_data = mkt_data.sort_values("order_month").reset_index(drop=True)
        aug_idx_list = mkt_data.index[mkt_data['order_month'] == '2018-08-01'].tolist()
        active_idx = aug_idx_list[0] if aug_idx_list else len(mkt_data) - 2
        
        active_mkt = mkt_data.iloc[active_idx]
        prev_mkt = mkt_data.iloc[active_idx - 1]
        
        st.subheader("Customer Metrics (Aug 2018)")
        col1, col2, col3 = st.columns(3)
        col1.metric("Repeat Order Share", f"{active_mkt['repeat_order_share_pct']}%", f"{active_mkt['repeat_order_share_pct'] - prev_mkt['repeat_order_share_pct']:.1f}% MoM")
        col2.metric("Avg Review Score", f"{active_mkt['avg_review_score']}", f"{active_mkt['avg_review_score'] - prev_mkt['avg_review_score']:.2f} MoM")
        
        acq_growth = ((active_mkt['new_customers_acquired'] - prev_mkt['new_customers_acquired']) / max(1, prev_mkt['new_customers_acquired'])) * 100
        col3.metric("New Customers Acquired", format_num(active_mkt['new_customers_acquired']), f"{acq_growth:.1f}% MoM")
        
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            if not rfm_data.empty:
                st.markdown("### RFM Segment Distribution")
                fig_rfm = px.bar(rfm_data, x="rfm_segment", y="customer_count", text="customer_count", color_discrete_sequence=['#6366f1'])
                fig_rfm.update_traces(texttemplate='%{text:.2s}', textposition='outside', textfont=dict(color='#f3f4f6'))
                fig_rfm.update_layout(**chart_layout)
                fig_rfm.update_layout(height=350)
                st.plotly_chart(fig_rfm, use_container_width=True)
                
        with col_m2:
            if not cohort_data.empty:
                st.markdown("### Cohort Retention (Jan 2017)")
                st.info("💡 **How to read:** 0.4% retention means exactly 4 out of 1000 customers from this cohort returned to buy again this month. (Olist has naturally low retention).")
                jan_cohort = cohort_data[cohort_data['cohort_month'] == '2017-01-01'].copy()
                max_idx = max(jan_cohort['cohort_index'].max(), 12)
                # Pad missing months with 0
                full_index = pd.DataFrame({'cohort_index': range(1, int(max_idx) + 1)})
                jan_full = pd.merge(full_index, jan_cohort, on='cohort_index', how='left').fillna(0)
                
                fig_cohort = go.Figure()
                fig_cohort.add_trace(go.Scatter(x="Month " + jan_full['cohort_index'].astype(str), y=jan_full['retention_pct'], fill='tozeroy', marker_color='#10b981'))
                fig_cohort.update_layout(**chart_layout)
                fig_cohort.update_layout(yaxis=dict(range=[0, 1.2], ticksuffix='%', showgrid=True, gridcolor='rgba(255,255,255,0.05)', zeroline=False), height=350)
                st.plotly_chart(fig_cohort, use_container_width=True)

# --- 4. GEO & CATEGORIES TAB ---
with tab_geo:
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        if not geo_data.empty:
            st.markdown("### Top 10 States by Revenue")
            fig_geo = px.bar(geo_data, x="state", y="revenue", text="revenue", color_discrete_sequence=['#6366f1'])
            fig_geo.update_traces(texttemplate='%{text:.2s}', textposition='outside', textfont=dict(color='#f3f4f6'))
            fig_geo.update_layout(**chart_layout)
            fig_geo.update_layout(height=400)
            st.plotly_chart(fig_geo, use_container_width=True)
            
    with col_g2:
        if not cat_data.empty:
            st.markdown("### Category Performance (Revenue vs Rating)")
            cat_data['Category'] = cat_data['category_english'].str.replace('_', ' ')
            fig_cat = go.Figure()
            fig_cat.add_trace(go.Bar(x=cat_data['Category'], y=cat_data['revenue'], name="Revenue", marker_color='#6366f1'))
            fig_cat.add_trace(go.Scatter(x=cat_data['Category'], y=cat_data['avg_review_score'], name="Rating", yaxis="y2", marker_color='#ffc107', mode='lines+markers'))
            fig_cat.update_layout(**chart_layout)
            fig_cat.update_layout(
                yaxis=dict(title="Revenue (BRL)", showgrid=True, gridcolor='rgba(255,255,255,0.05)', zeroline=False),
                yaxis2=dict(title="Rating", overlaying="y", side="right", range=[3.0, 5.0], showgrid=False, zeroline=False),
                height=400,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_cat, use_container_width=True)
            
    if not pay_data.empty:
        st.markdown("### Payment Trends")
        pay_data['Month'] = pd.to_datetime(pay_data['order_month']).dt.strftime('%Y-%m')
        pay_filtered = pay_data[(pay_data['Month'] >= '2017-01') & (pay_data['Month'] <= '2018-08')]
        
        # Plotly Area Chart
        fig_pay = px.area(pay_filtered, x="Month", y="payment_value", color="payment_type", 
                          color_discrete_sequence=['#6366f1', '#10b981', '#f59e0b', '#ef4444'])
        fig_pay.update_layout(**chart_layout)
        fig_pay.update_layout(height=400)
        st.plotly_chart(fig_pay, use_container_width=True)

