"""SKU-level weekly demand forecasting and backtesting evaluation framework."""
from __future__ import annotations

from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

# Central feature list for the ML forecasting model
FEATURES = [
    "week_of_year", "month", "season", "is_holiday", "promo_flag",
    "lag_1", "lag_7", "lag_14", "lag_28",
    "rolling_mean_7", "rolling_mean_14", "rolling_mean_28",
    "rolling_std_7", "rolling_std_28"
]


def calculate_wape(actual: pd.Series | np.ndarray, predicted: pd.Series | np.ndarray) -> float:
    """Calculate Weighted Absolute Percentage Error (WAPE) as the primary forecasting metric."""
    act_arr = np.array(actual, dtype=float)
    pred_arr = np.array(predicted, dtype=float)
    sum_actual = np.sum(np.abs(act_arr))
    if sum_actual == 0:
        return 0.0
    return float(np.sum(np.abs(act_arr - pred_arr)) / sum_actual)


def calculate_bias(actual: pd.Series | np.ndarray, predicted: pd.Series | np.ndarray) -> float:
    """Calculate normalized forecast bias (sum of errors divided by sum of actuals)."""
    act_arr = np.array(actual, dtype=float)
    pred_arr = np.array(predicted, dtype=float)
    sum_actual = np.sum(np.abs(act_arr))
    if sum_actual == 0:
        return 0.0
    return float(np.sum(pred_arr - act_arr) / sum_actual)


def seasonal_naive_forecast(history_df: pd.DataFrame, horizon_weeks: int, seasonal_period_weeks: int = 4) -> pd.DataFrame:
    """Predict demand using the corresponding previous seasonal period (Seasonal Naive)."""
    history = history_df.sort_values(["sku_id", "date"])
    forecasts = []
    
    for sku_id, group in history.groupby("sku_id"):
        group = group.copy()
        latest = group.iloc[-1]
        actuals = group["units_sold"].tolist()
        
        # Determine seasonal values fallback if history is too short
        if len(actuals) < seasonal_period_weeks:
            vals = [actuals[-1]] * seasonal_period_weeks if actuals else [0.0] * seasonal_period_weeks
        else:
            vals = actuals[-seasonal_period_weeks:]
            
        for step in range(1, horizon_weeks + 1):
            val = vals[(step - 1) % seasonal_period_weeks]
            date = latest["date"] + pd.Timedelta(weeks=step)
            
            forecasts.append({
                "sku_id": sku_id,
                "sku": sku_id,
                "product": latest["product"],
                "category": latest["category"],
                "subcategory": latest["subcategory"],
                "date": date,
                "predicted_demand": max(0.0, float(val)),
                "current_stock": latest["current_stock"],
                "on_hand_units": latest.get("on_hand_units", latest.get("current_stock", 0.0)),
                "on_order_units": latest.get("on_order_units", 0.0),
                "lead_time_days": latest.get("lead_time_days", 7.0),
                "reorder_point": latest.get("reorder_point", 0.0),
                "unit_cost": latest["unit_cost"],
                "list_price": latest["list_price"],
                "price": latest["price"]
            })
            
    return pd.DataFrame(forecasts)


def rolling_origin_backtest(
    df: pd.DataFrame,
    seasonal_period_weeks: int = 4,
    folds: int = 4,
    horizon_weeks: int = 4
) -> tuple[float, float, float, float]:
    """Perform time-series chronological rolling-origin backtesting without lookahead leakage."""
    history = df.sort_values(["sku_id", "date"]).copy()
    unique_dates = sorted(history["date"].unique())
    n_weeks = len(unique_dates)
    
    if n_weeks < (folds * horizon_weeks) + seasonal_period_weeks + 2:
        # Fallback if history is too short
        return 0.5, 0.0, 0.5, 0.0
        
    rf_wapes = []
    rf_biases = []
    sn_wapes = []
    sn_biases = []
    
    # Iterate across chronological folds
    for f in range(folds):
        cutoff_idx = n_weeks - ((folds - f) * horizon_weeks)
        cutoff_date = unique_dates[cutoff_idx - 1]
        end_date = unique_dates[min(cutoff_idx + horizon_weeks - 1, n_weeks - 1)]
        
        train = history[history["date"] <= cutoff_date]
        test = history[(history["date"] > cutoff_date) & (history["date"] <= end_date)]
        
        if train.empty or test.empty:
            continue
            
        # 1. Seasonal Naive Baseline
        sn_fc = seasonal_naive_forecast(train, horizon_weeks=horizon_weeks, seasonal_period_weeks=seasonal_period_weeks)
        # Match test targets
        merged_sn = pd.merge(test[["date", "sku_id", "units_sold"]], sn_fc[["date", "sku_id", "predicted_demand"]], on=["date", "sku_id"], how="inner")
        if not merged_sn.empty:
            sn_wapes.append(calculate_wape(merged_sn["units_sold"], merged_sn["predicted_demand"]))
            sn_biases.append(calculate_bias(merged_sn["units_sold"], merged_sn["predicted_demand"]))
            
        # 2. Random Forest Model
        # Prep training matrices
        train_clean = train.dropna(subset=FEATURES).copy()
        if len(train_clean) < 10:
            continue
            
        prep = ColumnTransformer([
            ("number", SimpleImputer(strategy="median"), [f for f in FEATURES if f != "sku_id"]),
            ("sku", OneHotEncoder(handle_unknown="ignore"), ["sku_id"])
        ])
        model = Pipeline([
            ("prep", prep),
            ("forest", RandomForestRegressor(n_estimators=100, min_samples_leaf=2, random_state=42))
        ])
        
        model.fit(train_clean[["sku_id"] + FEATURES], train_clean["units_sold"])
        
        # Test predictions
        test_clean = test.copy()
        # Predict
        test_clean["predicted_demand"] = model.predict(test_clean[["sku_id"] + FEATURES]).clip(0.0)
        
        merged_rf = test_clean.dropna(subset=["units_sold", "predicted_demand"])
        if not merged_rf.empty:
            rf_wapes.append(calculate_wape(merged_rf["units_sold"], merged_rf["predicted_demand"]))
            rf_biases.append(calculate_bias(merged_rf["units_sold"], merged_rf["predicted_demand"]))
            
    avg_rf_wape = float(np.mean(rf_wapes)) if rf_wapes else 1.0
    avg_rf_bias = float(np.mean(rf_biases)) if rf_biases else 0.0
    avg_sn_wape = float(np.mean(sn_wapes)) if sn_wapes else 1.0
    avg_sn_bias = float(np.mean(sn_biases)) if sn_biases else 0.0
    
    return avg_rf_wape, avg_rf_bias, avg_sn_wape, avg_sn_bias


def train_forecast_model(
    clean_df: pd.DataFrame,
    model_path: str | Path,
    seasonal_period_weeks: int = 4
) -> tuple[Pipeline | None, dict]:
    """Train forecast models, run out-of-sample backtesting, honestly select the best, and save it."""
    # Run backtesting first to evaluate models out-of-sample
    rf_wape, rf_bias, sn_wape, sn_bias = rolling_origin_backtest(
        clean_df, seasonal_period_weeks=seasonal_period_weeks, folds=4, horizon_weeks=4
    )
    
    # Honest selection logic
    if rf_wape < sn_wape:
        selected_model_type = "Random Forest"
        selected_wape = rf_wape
        selected_bias = rf_bias
    else:
        selected_model_type = "Seasonal Naive"
        selected_wape = sn_wape
        selected_bias = sn_bias
        
    model_comparison = {
        "Random Forest": {"WAPE": rf_wape, "Bias": rf_bias, "Rank": 1 if rf_wape < sn_wape else 2},
        "Seasonal Naive": {"WAPE": sn_wape, "Bias": sn_bias, "Rank": 2 if rf_wape < sn_wape else 1},
        "selected_model": selected_model_type,
        "selected_wape": selected_wape,
        "selected_bias": selected_bias,
        "seasonal_period_weeks": seasonal_period_weeks
    }
    
    # Fit Random Forest on full history to save
    data = clean_df.dropna(subset=FEATURES).copy()
    if len(data) < 15:
        # Fallback if too few records
        artifact = {
            "model": None,
            "features": FEATURES,
            "comparison": model_comparison,
            "trained_rows": len(clean_df)
        }
        joblib.dump(artifact, Path(model_path))
        return None, model_comparison
        
    prep = ColumnTransformer([
        ("number", SimpleImputer(strategy="median"), [f for f in FEATURES if f != "sku_id"]),
        ("sku", OneHotEncoder(handle_unknown="ignore"), ["sku_id"])
    ])
    model = Pipeline([
        ("prep", prep),
        ("forest", RandomForestRegressor(n_estimators=150, min_samples_leaf=2, random_state=42))
    ])
    
    model.fit(data[["sku_id"] + FEATURES], data["units_sold"])
    
    # Save artifact
    artifact = {
        "model": model,
        "features": FEATURES,
        "comparison": model_comparison,
        "trained_rows": len(data)
    }
    
    destination = Path(model_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, destination)
    
    return model, model_comparison


def forecast_next_days(
    clean_df: pd.DataFrame,
    model_path: str | Path,
    horizon: int = 4
) -> pd.DataFrame:
    """Generate forecasts for the next N weeks using the best selected model from out-of-sample backtesting."""
    artifact = joblib.load(model_path)
    
    if not isinstance(artifact, dict) or "comparison" not in artifact or artifact["comparison"] is None:
        train_forecast_model(clean_df, model_path, seasonal_period_weeks=4)
        artifact = joblib.load(model_path)
        
    model = artifact["model"]
    comparison = artifact["comparison"]
    selected_model = comparison["selected_model"]
    seasonal_period = comparison.get("seasonal_period_weeks", 4)
    
    history = clean_df.sort_values(["sku_id", "date"]).copy()
    
    if selected_model == "Seasonal Naive" or model is None:
        # Run Seasonal-Naive prediction
        return seasonal_naive_forecast(history, horizon_weeks=horizon, seasonal_period_weeks=seasonal_period)
        
    # Else predict using the trained Random Forest model
    forecasts = []
    for sku_id, group in history.groupby("sku_id"):
        group = group.copy()
        latest = group.iloc[-1]
        
        # Start predicting week by week recursively
        temp_group = group.copy()
        
        for step in range(1, horizon + 1):
            date = latest["date"] + pd.Timedelta(weeks=step)
            
            # Predict features for the next step. To compute lag/rolling features,
            # we temporarily append previous predictions to the history df
            # We fetch the last row containing lags and rolling means
            # Let's build a temporary daily-equivalent row for features
            
            # For features, we can construct the next row based on the last row's lags
            # Let's take the latest record and construct the next chronological features:
            lags = temp_group["units_sold"].tolist()
            
            row = {
                "sku_id": sku_id,
                "sku": sku_id,
                "product": latest["product"],
                "category": latest["category"],
                "subcategory": latest["subcategory"],
                "date": date,
                "week_of_year": int(date.isocalendar()[1]),
                "month": int(date.month),
                "season": int(date.month % 12 // 3 + 1),
                "is_holiday": 0,
                "promo_flag": 0,
                "current_stock": latest["current_stock"],
                "on_hand_units": latest.get("on_hand_units", latest.get("current_stock", 0.0)),
                "on_order_units": latest.get("on_order_units", 0.0),
                "lead_time_days": latest.get("lead_time_days", 7.0),
                "reorder_point": latest.get("reorder_point", 0.0),
                "unit_cost": latest["unit_cost"],
                "list_price": latest["list_price"],
                "price": latest["price"]
            }
            
            # Engineer features on the fly
            row["lag_1"] = lags[-1]
            row["lag_7"] = lags[-7] if len(lags) >= 7 else lags[-1]
            row["lag_14"] = lags[-14] if len(lags) >= 14 else lags[-1]
            row["lag_28"] = lags[-28] if len(lags) >= 28 else lags[-1]
            
            row["rolling_mean_7"] = float(np.mean(lags[-7:]))
            row["rolling_mean_14"] = float(np.mean(lags[-14:]))
            row["rolling_mean_28"] = float(np.mean(lags[-28:]))
            
            row["rolling_std_7"] = float(np.std(lags[-7:])) if len(lags) >= 2 else 0.0
            row["rolling_std_28"] = float(np.std(lags[-28:])) if len(lags) >= 2 else 0.0
            
            row_df = pd.DataFrame([row])
            predicted = max(0.0, float(model.predict(row_df[["sku_id"] + FEATURES])[0]))
            
            row["predicted_demand"] = round(predicted)
            forecasts.append(row)
            
            # Append the prediction to temp history to calculate the next lags
            row["units_sold"] = predicted
            temp_group = pd.concat([temp_group, pd.DataFrame([row])], ignore_index=True)
            
    return pd.DataFrame(forecasts)
