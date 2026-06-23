import os
import yaml
import duckdb
import pandas as pd
import numpy as np
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from sklearn.metrics import mean_squared_error, mean_absolute_error
from sklearn.ensemble import RandomForestRegressor
from src.utils.logger import setup_logger

logger = setup_logger("train_forecasting")

try:
    from xgboost import XGBRegressor
    XGBOOST_AVAILABLE = True
except Exception as e:
    logger.warning(f"XGBoost could not be loaded (likely missing OpenMP/libomp.dylib on macOS): {str(e)}. Falling back to RandomForestRegressor.")
    XGBOOST_AVAILABLE = False

def load_config(config_path="configs/pipeline_config.yaml"):
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

def create_features(df, label=None):
    """Creates time series features from a daily DataFrame."""
    df = df.copy()
    df["day_of_week"] = df.index.dayofweek
    df["day_of_month"] = df.index.day
    df["month"] = df.index.month
    df["year"] = df.index.year
    
    # Lag features
    df["lag_1"] = df[label].shift(1)
    df["lag_7"] = df[label].shift(7)
    df["lag_14"] = df[label].shift(14)
    
    # Rolling window features
    df["rolling_mean_7"] = df[label].shift(1).rolling(window=7).mean()
    df["rolling_mean_30"] = df[label].shift(1).rolling(window=30).mean()
    
    return df.dropna()

def run_forecasting():
    config = load_config()
    db_path = config["paths"]["gold_db_path"]
    gold_dir = config["paths"]["gold_dir"]
    forecast_days = config["ml"]["forecast_horizon_days"]
    
    logger.info("Connecting to DuckDB for Demand Forecasting...")
    conn = duckdb.connect(db_path)
    
    # 1. Aggregate orders and revenue to a daily grain
    logger.info("Extracting daily aggregated orders and revenue...")
    query = """
        SELECT 
            d.date,
            count(distinct f.order_id) AS total_orders,
            sum(f.subtotal) AS total_revenue
        FROM fact_orders f
        JOIN dim_date d ON f.date_key = d.date_key
        GROUP BY d.date
        ORDER BY d.date
    """
    df = conn.execute(query).df()
    
    if len(df) == 0:
        logger.error("No daily data found. Run medallion pipeline first.")
        conn.close()
        return
        
    df["date"] = pd.to_datetime(df["date"])
    df.set_index("date", inplace=True)
    
    # Fill any calendar gaps (ensure continuous daily timeline)
    df = df.asfreq("D", fill_value=0)
    
    logger.info(f"Daily timeline spans {len(df)} days. Training forecasting models on 'total_revenue'...")
    
    # 2. Train-Test Split (Last 30 days as test set)
    test_size = 30
    train_df = df.iloc[:-test_size]
    test_df = df.iloc[-test_size:]
    
    # Target variable
    target = "total_revenue"
    
    # --- MODEL 1: Statsmodels Holt-Winters Exponential Smoothing ---
    logger.info("Training Holt-Winters Exponential Smoothing...")
    hw_model = ExponentialSmoothing(
        train_df[target],
        seasonal_periods=7, # weekly cycle
        trend="add",
        damped_trend=True,
        seasonal="add",
        initialization_method="estimated"
    )
    hw_fit = hw_model.fit()
    hw_test_preds = np.clip(hw_fit.forecast(len(test_df)), 0, None)
    
    hw_rmse = np.sqrt(mean_squared_error(test_df[target], hw_test_preds))
    hw_mae = mean_absolute_error(test_df[target], hw_test_preds)
    logger.info(f"Holt-Winters - Test RMSE: {hw_rmse:.2f}, Test MAE: {hw_mae:.2f}")
    
    # --- MODEL 2: Machine Learning Regressor (XGBoost or RandomForest fallback) ---
    feature_cols = ["day_of_week", "day_of_month", "month", "lag_1", "lag_7", "lag_14", "rolling_mean_7", "rolling_mean_30"]
    df_feat = create_features(df, label=target)
    
    # Re-split features
    train_feat = df_feat.loc[df_feat.index < test_df.index[0]]
    test_feat = df_feat.loc[df_feat.index >= test_df.index[0]]
    
    if XGBOOST_AVAILABLE:
        logger.info("Training XGBoost Regressor...")
        ml_model = XGBRegressor(n_estimators=100, learning_rate=0.05, random_state=42)
        ml_model_name = "XGBoost"
    else:
        logger.info("Training RandomForest Regressor (XGBoost Fallback)...")
        ml_model = RandomForestRegressor(n_estimators=100, random_state=42)
        ml_model_name = "RandomForest"
        
    ml_model.fit(train_feat[feature_cols], train_feat[target])
    xgb_test_preds = np.clip(ml_model.predict(test_feat[feature_cols]), 0, None)
    
    xgb_rmse = np.sqrt(mean_squared_error(test_feat[target], xgb_test_preds))
    xgb_mae = mean_absolute_error(test_feat[target], xgb_test_preds)
    logger.info(f"{ml_model_name} - Test RMSE: {xgb_rmse:.2f}, Test MAE: {xgb_mae:.2f}")
    
    # MLflow tracking has been disabled by user request.
    
    # 3. Generate Future Forecast (Next 30 days)
    # We will use the better model. Let's compare and pick the best one.
    best_model_name = ml_model_name if xgb_rmse < hw_rmse else "Holt-Winters"
    logger.info(f"Picking best model based on RMSE: {best_model_name}")
    
    future_dates = pd.date_range(start=df.index[-1] + pd.Timedelta(days=1), periods=forecast_days, freq="D")
    
    if best_model_name == "Holt-Winters":
        # Holt-Winters makes multi-step out-of-sample forecasts natively
        future_forecast = hw_fit.forecast(test_size + forecast_days)[test_size:]
    else:
        # ML model requires recursive forecasting for future lags
        future_forecast = []
        current_data = df_feat.copy()
        
        # Recursive prediction loop
        for f_date in future_dates:
            # Add new empty row for the future date
            new_row = pd.DataFrame(index=[f_date], columns=df.columns)
            new_row.loc[f_date, target] = np.nan
            current_data = pd.concat([current_data, new_row])
            
            # Recompute features for the final row
            feats = create_features(current_data, label=target)
            last_feat = feats.iloc[[-1]]
            
            # Predict
            pred = ml_model.predict(last_feat[feature_cols])[0]
            future_forecast.append(pred)
            
            # Set the actual target to our prediction for the next lag iterations
            current_data.loc[f_date, target] = pred
            
    # 4. Save predictions to a DuckDB Gold table: forecast_predictions
    logger.info("Writing forecast predictions back to DuckDB...")
    
    forecast_df = pd.DataFrame({
        "forecast_date": future_dates.strftime("%Y-%m-%d"),
        "predicted_revenue": np.round(np.clip(future_forecast, 0, None), 2),
        "model_used": best_model_name
    })
    
    conn.execute("DROP TABLE IF EXISTS forecast_predictions;")
    conn.execute("""
        CREATE TABLE forecast_predictions (
            forecast_date DATE PRIMARY KEY,
            predicted_revenue DOUBLE,
            model_used VARCHAR
        );
    """)
    
    # Insert from pandas dataframe
    conn.execute("INSERT INTO forecast_predictions SELECT * FROM forecast_df")
    
    # Save test predictions for visualization vs actuals
    # Save a record of the last 30 days actual vs predictions
    history_df = pd.DataFrame({
        "date": test_df.index.strftime("%Y-%m-%d"),
        "actual_revenue": np.round(test_df[target].values, 2),
        "predicted_revenue_hw": np.round(hw_test_preds.values, 2),
        "predicted_revenue_xgb": np.round(xgb_test_preds, 2)
    })
    conn.execute("DROP TABLE IF EXISTS forecast_evaluation;")
    conn.execute("""
        CREATE TABLE forecast_evaluation (
            date DATE PRIMARY KEY,
            actual_revenue DOUBLE,
            predicted_revenue_hw DOUBLE,
            predicted_revenue_xgb DOUBLE
        );
    """)
    conn.execute("INSERT INTO forecast_evaluation SELECT * FROM history_df")
    
    logger.info("Forecasting predictions successfully saved to database:")
    sample = conn.execute("SELECT * FROM forecast_predictions LIMIT 5").df()
    logger.info("\n" + str(sample))
    
    conn.close()
    logger.info("Forecasting pipeline completed successfully!")

if __name__ == "__main__":
    run_forecasting()
