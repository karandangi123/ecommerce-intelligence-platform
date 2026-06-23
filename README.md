<div align="center">
  <img src="https://img.shields.io/badge/Python-3.14-blue.svg?style=for-the-badge&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/DuckDB-Fast%20OLAP-yellow.svg?style=for-the-badge&logo=duckdb" alt="DuckDB">
  <img src="https://img.shields.io/badge/Streamlit-App-FF4B4B.svg?style=for-the-badge&logo=streamlit" alt="Streamlit">
  <img src="https://img.shields.io/badge/Polars-Blazing%20Fast-pink.svg?style=for-the-badge&logo=polars" alt="Polars">
  <img src="https://img.shields.io/badge/Machine%20Learning-Scikit--Learn-orange.svg?style=for-the-badge&logo=scikitlearn" alt="Machine Learning">
</div>

<br>

<h1 align="center">🛒 E-Commerce Intelligence Platform</h1>

<p align="center">
  <b>An end-to-end Enterprise Analytics Engine processing 33.8 Million rows of transactional data.</b><br>
  Built with a modern Medallion Architecture (DuckDB), Machine Learning Pipelines (K-Means, Isolation Forest), and an interactive Premium Glassmorphism UI.
</p>

---

## 🌟 Overview

This project transforms the massive **Instacart Market Basket Dataset (3.4M orders, 33.8M item purchases)** into a highly optimized, lightning-fast analytical data warehouse. 

It is designed to showcase senior-level capabilities in **Data Engineering**, **Machine Learning**, and **Business Analytics**. By replacing slow Pandas dataframes with **DuckDB** and **Polars**, this system processes millions of rows in milliseconds, entirely locally without requiring expensive cloud infrastructure.

### 👤 Author
**Karan Dangi**
*Data Scientist & Analytics Engineer*

---

## 🏗️ Architecture & Tech Stack

### 1. Data Engineering (Medallion Architecture)
*   **Bronze Layer**: Raw CSV extracts from Instacart.
*   **Silver Layer (Polars + Pandas)**: Cleansed and standardized data mapped into Parquet formats.
*   **Gold Layer (DuckDB)**: Modeled into a Star Schema (`fact_orders`, `dim_customers`, `dim_products`) optimized for columnar OLAP queries.
*   **Data Quality Engine**: Evaluates the warehouse on 6 critical dimensions (Completeness, Uniqueness, Validity, Consistency, Freshness, Statistical Profiling) resulting in a perfect 100% DQ score.

### 2. Machine Learning Operations (MLOps)
*   **Customer Segmentation**: Unsupervised `K-Means Clustering` grouping 200,000+ customers into distinct behavioral segments based on RFM (Recency, Frequency, Monetary) metrics.
*   **Anomaly Detection**: `Isolation Forest` isolating irregular transaction days and supply-chain volume spikes.
*   **Market Basket Analysis**: Multi-threaded `Polars` cartesian self-joins analyzing 22M+ cart pairings to calculate Association Rules (Support, Confidence, Lift) for cross-selling recommendations.

### 3. Business Intelligence (Streamlit)
A modern, **Premium Glassmorphism Dashboard** consisting of 5 distinct views:
1.  **Executive Summary**: MoM Growth, Daily Revenue anomalies, and AI-driven business insights.
2.  **Customer Intelligence**: Cohort Retention Heatmaps, RFM Matrices, and ML Cluster distributions.
3.  **Product Analytics**: ABC Inventory Pareto curves and Department cross-penetration logic.
4.  **Basket Intelligence**: Association rule engines (e.g., Apple + Strawberry bundles with 67x Lift).
5.  **Data Quality**: Global warehouse health metrics and table-by-table integrity scores.

---

## 🚀 Getting Started

### Prerequisites
* Python 3.9+
* Pip (Virtual environment recommended)

### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/karandangi123/ecommerce-intelligence-platform.git
   cd ecommerce-intelligence-platform
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the Data Pipeline (ETL & SQL Views):
   ```bash
   python -m src.transformation.medallion_pipeline
   ```

4. Run the Data Quality Framework:
   ```bash
   python -m src.transformation.data_quality_report
   ```

5. Run the Machine Learning Pipelines:
   ```bash
   python -m src.ml.train_segmentation
   python -m src.ml.anomaly_detection
   python -m src.ml.train_recommendations
   python -m src.ai_insights.gemini_summarizer
   ```

6. Launch the Dashboard:
   ```bash
   streamlit run app/dashboard.py
   ```

---

## 🧪 Automated Testing
This project utilizes `pytest` to guarantee pipeline integrity. The test suite verifies the presence, schemas, and non-empty status of the Gold Layer tables, ML outputs, and Advanced Analytical Views.
```bash
pytest tests/test_pipeline.py -v
```

---

## 📄 Detailed Report & Recruiter Guide
Included in this repository is a massive, comprehensive PDF document:
`Instacart_ECommerce_Platform_Detailed_Report.pdf`

This document contains line-by-line code explanations, architecture decisions, metric logic, and a dedicated **Recruiter Q&A** section designed for technical interviews. 

---
*Developed with 💡 by Karan Dangi.*
