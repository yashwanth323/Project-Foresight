"""Data ingestion, validation, cleaning, and weekly aggregation for Project FORESIGHT pipeline."""
from __future__ import annotations

import os
from pathlib import Path
import numpy as np
import pandas as pd

REQUIRED_COLUMNS_SALES = {"date", "sku_id", "units_sold", "revenue", "unit_price", "promo_flag"}
REQUIRED_COLUMNS_MASTER = {"sku_id", "category", "subcategory", "launch_date", "unit_cost", "list_price"}
REQUIRED_COLUMNS_CALENDAR = {"date", "week", "month", "season", "is_holiday", "promo_event"}
REQUIRED_COLUMNS_INVENTORY = {"date", "sku_id", "on_hand_units", "on_order_units", "lead_time_days", "reorder_point"}


def create_demo_sales(path_dir: str | Path, periods: int = 180) -> None:
    """Create reproducible fallback CSV files representing the four official tables if not present."""
    rng = np.random.default_rng(42)
    path_dir = Path(path_dir)
    path_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. SKU Master Catalog
    catalog = [
        ("MILK-1L", "Milk 1L", "Dairy", "Fresh Milk", 30.0, 42.0, "2025-01-01"),
        ("RICE-5K", "Rice 5kg", "Grocery", "Grains", 280.0, 360.0, "2025-01-01"),
        ("BREAD-WHT", "White Bread", "Bakery", "Sliced Bread", 22.0, 34.0, "2025-01-01"),
        ("SHAM-400", "Shampoo 400ml", "Personal Care", "Hair Care", 140.0, 198.0, "2025-01-01"),
        ("CHIP-200", "Potato Chips 200g", "Snacks", "Chips", 32.0, 48.0, "2025-01-01"),
    ]
    sku_master_rows = []
    for sku_id, product, cat, subcat, cost, price, launch in catalog:
        sku_master_rows.append({
            "sku_id": sku_id,
            "product": product,
            "category": cat,
            "subcategory": subcat,
            "unit_cost": cost,
            "list_price": price,
            "launch_date": launch
        })
    pd.DataFrame(sku_master_rows).to_csv(path_dir / "sku_master.csv", index=False)
    
    # Generate Date Range
    dates = pd.date_range(end=pd.Timestamp.today().normalize(), periods=periods)
    
    # 2. Calendar Table
    calendar_rows = []
    for date in dates:
        weekend = date.dayofweek >= 5
        season = date.month % 12 // 3 + 1
        holiday = int(date.day in (1, 15) or (date.month == 12 and date.day > 20))
        promo_event = "Holiday Promo" if holiday else "Weekend Special" if weekend else "None"
        calendar_rows.append({
            "date": date.date(),
            "week": date.isocalendar()[1],
            "month": date.month,
            "season": season,
            "is_holiday": holiday,
            "promo_event": promo_event
        })
    pd.DataFrame(calendar_rows).to_csv(path_dir / "calendar.csv", index=False)
    
    # 3. Sales Daily & 4. Inventory Snapshots Tables
    sales_rows = []
    inventory_rows = []
    
    for sku_id, product, _, _, _, price, _ in catalog:
        # Base daily sales parameter
        base_demand = 120 if sku_id == "MILK-1L" else 58 if sku_id == "RICE-5K" else 88 if sku_id == "BREAD-WHT" else 33 if sku_id == "SHAM-400" else 51
        lead_time = 7 if sku_id == "MILK-1L" else 10 if sku_id == "RICE-5K" else 5
        reorder_pt = base_demand * (lead_time + 3) # Reorder point calculation
        current_stock = base_demand * 10
        on_order = 0
        
        for i, date in enumerate(dates):
            weekend = 1.12 if date.dayofweek >= 5 else 1.0
            seasonal = 1 + .14 * np.sin(i / 12)
            holiday = 1.25 if date.day in (1, 15) or (date.month == 12 and date.day > 20) else 1.0
            promo_flag = 1 if (date.dayofweek == 6 or holiday > 1.0) else 0
            promo_boost = 1.18 if promo_flag == 1 else 1.0
            
            quantity = max(0, round(base_demand * weekend * seasonal * holiday * promo_boost + rng.normal(0, 5)))
            revenue = round(quantity * price, 2)
            
            # Inventory snap simulation
            current_stock = max(0, current_stock - quantity)
            
            # Simple order trigger simulation
            if current_stock < reorder_pt and on_order == 0:
                on_order = base_demand * 12
                
            # If lead time ends, order arrives
            if on_order > 0 and i % lead_time == 0:
                current_stock += on_order
                on_order = 0
                
            sales_rows.append({
                "date": date.date(),
                "sku_id": sku_id,
                "units_sold": quantity,
                "revenue": revenue,
                "unit_price": price,
                "promo_flag": promo_flag
            })
            
            # Periodic inventory snapshot simulation (e.g. inventory recorded every 3 days)
            if i % 3 == 0:
                inventory_rows.append({
                    "date": date.date(),
                    "sku_id": sku_id,
                    "on_hand_units": current_stock,
                    "on_order_units": on_order,
                    "lead_time_days": lead_time,
                    "reorder_point": reorder_pt
                })
            
    pd.DataFrame(sales_rows).to_csv(path_dir / "sales_daily.csv", index=False)
    pd.DataFrame(inventory_rows).to_csv(path_dir / "inventory_snapshots.csv", index=False)


def load_data(raw_dir: str | Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load the four raw CSV tables and return them as dataframes."""
    raw_dir = Path(raw_dir)
    
    sales = pd.read_csv(raw_dir / "sales_daily.csv")
    master = pd.read_csv(raw_dir / "sku_master.csv")
    cal = pd.read_csv(raw_dir / "calendar.csv")
    inv = pd.read_csv(raw_dir / "inventory_snapshots.csv")
    
    return sales, master, cal, inv


def validate_data(sales: pd.DataFrame, master: pd.DataFrame, cal: pd.DataFrame, inv: pd.DataFrame) -> None:
    """Validate schemas, data types, and required columns in raw tables."""
    for table_name, df, req_cols in [
        ("sales_daily", sales, REQUIRED_COLUMNS_SALES),
        ("sku_master", master, REQUIRED_COLUMNS_MASTER),
        ("calendar", cal, REQUIRED_COLUMNS_CALENDAR),
        ("inventory_snapshots", inv, REQUIRED_COLUMNS_INVENTORY),
    ]:
        missing = req_cols - set(df.columns)
        if missing:
            raise ValueError(f"Missing required columns in table '{table_name}': {sorted(missing)}")


def clean_data(sales: pd.DataFrame, master: pd.DataFrame, cal: pd.DataFrame, inv: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Clean data type structures, format dates, drop duplicates and validate labels."""
    for df in [sales, cal, inv]:
        df["date"] = pd.to_datetime(df["date"])
    master["launch_date"] = pd.to_datetime(master["launch_date"])
    
    master["sku_id"] = master["sku_id"].astype(str).str.strip()
    sales["sku_id"] = sales["sku_id"].astype(str).str.strip()
    inv["sku_id"] = inv["sku_id"].astype(str).str.strip()
    
    sales = sales.drop_duplicates(subset=["date", "sku_id"], keep="last")
    inv = inv.drop_duplicates(subset=["date", "sku_id"], keep="last")
    cal = cal.drop_duplicates(subset=["date"], keep="last")
    master = master.drop_duplicates(subset=["sku_id"], keep="last")
    
    sales["units_sold"] = pd.to_numeric(sales["units_sold"], errors="coerce").fillna(0).clip(lower=0)
    sales["revenue"] = pd.to_numeric(sales["revenue"], errors="coerce").fillna(0).clip(lower=0)
    inv["on_hand_units"] = pd.to_numeric(inv["on_hand_units"], errors="coerce").fillna(0).clip(lower=0)
    inv["on_order_units"] = pd.to_numeric(inv["on_order_units"], errors="coerce").fillna(0).clip(lower=0)
    
    return sales, master, cal, inv


def merge_data(sales: pd.DataFrame, master: pd.DataFrame, cal: pd.DataFrame, inv: pd.DataFrame) -> pd.DataFrame:
    """Merge the cleaned tables into a daily master dataframe using LEFT joins and merge_asof to forward-fill inventory snapshots."""
    # 1. Join sales (fact table) with sku_master using LEFT join to preserve all sales records
    df = pd.merge(sales, master, on="sku_id", how="left")
    
    # 2. Join with calendar on date using LEFT join
    df = pd.merge(df, cal, on="date", how="left")
    
    # 3. Join with inventory_snapshots using pd.merge_asof.
    # Snapshots are periodic, so we forward-fill inventory snapshots using backward direction matching.
    df = df.sort_values("date")
    inv = inv.sort_values("date")
    
    # merge_asof requires the sorting key to be numeric or datetime.
    merged = pd.merge_asof(
        df,
        inv,
        on="date",
        by="sku_id",
        direction="backward"
    )
    
    # Fill remaining NaNs in inventory fields with default values
    merged["on_hand_units"] = merged["on_hand_units"].fillna(0.0)
    merged["on_order_units"] = merged["on_order_units"].fillna(0.0)
    merged["lead_time_days"] = merged["lead_time_days"].fillna(7.0)
    merged["reorder_point"] = merged["reorder_point"].fillna(0.0)
    
    return merged.sort_values(["sku_id", "date"])


def aggregate_weekly(daily_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate daily master dataframe to weekly intervals starting on Mondays."""
    # Create week start identifier (resampled starting Monday)
    daily_df["week_start"] = daily_df["date"].dt.to_period("W").dt.start_time
    
    # Grouping aggregations
    weekly = daily_df.groupby(["sku_id", "week_start"]).agg(
        # Sum target units sold and revenue
        units_sold=("units_sold", "sum"),
        revenue=("revenue", "sum"),
        # Get matching metadata
        product=("product", "first"),
        category=("category", "first"),
        subcategory=("subcategory", "first"),
        unit_cost=("unit_cost", "first"),
        list_price=("list_price", "first"),
        # Snapshots: take last daily record of the week
        on_hand_units=("on_hand_units", "last"),
        on_order_units=("on_order_units", "last"),
        lead_time_days=("lead_time_days", "last"),
        reorder_point=("reorder_point", "last"),
        # Promo flags: max is 1 if any daily promo was active during the week
        promo_flag=("promo_flag", "max"),
        is_holiday=("is_holiday", "max")
    ).reset_index()
    
    # Alias columns for existing dashboard code compatibility
    weekly["sku"] = weekly["sku_id"]
    weekly["date"] = weekly["week_start"]
    weekly["quantity_sold"] = weekly["units_sold"]
    weekly["current_stock"] = weekly["on_hand_units"]
    weekly["price"] = weekly["list_price"]
    weekly["holiday"] = weekly["is_holiday"]
    
    # Get week index, month, season
    weekly["week_of_year"] = weekly["date"].dt.isocalendar().week.astype(int)
    weekly["month"] = weekly["date"].dt.month.astype(int)
    weekly["season"] = weekly["date"].dt.month % 12 // 3 + 1
    
    return weekly.sort_values(["sku_id", "date"])


def prepare_features(weekly_df: pd.DataFrame) -> pd.DataFrame:
    """Engineer lags and rolling statistics without temporal data leakage."""
    df = weekly_df.sort_values(["sku_id", "date"]).copy()
    
    # Generate lags (1, 7, 14, 28 weeks)
    for lag in [1, 7, 14, 28]:
        df[f"lag_{lag}"] = df.groupby("sku_id")["units_sold"].shift(lag)
        
    # Generate rolling statistics (means and stds over 7, 14, 28 weeks)
    # MUST shift by 1 before calculating to avoid lookahead/leakage!
    for window in [7, 14, 28]:
        df[f"rolling_mean_{window}"] = df.groupby("sku_id")["units_sold"].transform(
            lambda x: x.shift(1).rolling(window, min_periods=1).mean()
        )
        df[f"rolling_std_{window}"] = df.groupby("sku_id")["units_sold"].transform(
            lambda x: x.shift(1).rolling(window, min_periods=1).std()
        ).fillna(0.0)
        
    return df


def run_pipeline(raw_dir: str | Path, output_file: str | Path) -> pd.DataFrame:
    """Ingest, clean, merge, aggregate, engineer features, and save the weekly file."""
    raw_dir = Path(raw_dir)
    output_file = Path(output_file)
    
    # Auto create demo datasets if missing in the raw folder
    if not (raw_dir / "sales_daily.csv").exists():
        create_demo_sales(raw_dir)
        
    sales, master, cal, inv = load_data(raw_dir)
    validate_data(sales, master, cal, inv)
    sales, master, cal, inv = clean_data(sales, master, cal, inv)
    daily_merged = merge_data(sales, master, cal, inv)
    weekly_aggregated = aggregate_weekly(daily_merged)
    model_ready = prepare_features(weekly_aggregated)
    
    output_file.parent.mkdir(parents=True, exist_ok=True)
    model_ready.to_csv(output_file, index=False)
    
    return model_ready


if __name__ == "__main__":
    # Test execution
    root = Path(__file__).resolve().parents[1]
    run_pipeline(root / "data" / "raw", root / "data" / "processed" / "sales_clean_weekly.csv")
    print("Pipeline run completed successfully.")
