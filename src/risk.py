"""Inventory risk scoring, replenishment decisions, and financial business impact calculations."""
from __future__ import annotations

import numpy as np
import pandas as pd

# Central configuration for all risk parameters and thresholds
# Reasoning:
# - safety_stock_days: Buffer of 3 days to protect against demand spikes and lead-time delays.
# - overstock_weeks_window: 6 weeks (42 days) of forward coverage. Stock above this level is inactive capital.
# - stockout_trigger_ratio: If stock is less than 1.0x of demand during lead time, reorder is required.
# - overstock_trigger_ratio: If stock exceeds 1.5x of expected demand in the forward window, markdown is recommended.
RISK_CONFIG = {
    "safety_stock_days": 3,
    "overstock_weeks_window": 6,
    "stockout_trigger_ratio": 1.0,
    "overstock_trigger_ratio": 1.5,
}


def score_inventory_risk(forecast_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate stockout/overstock risk scores, decision actions, and Rupee financial impact per SKU.
    
    Transparent risk logic:
    1. Stockout Risk:
       - Compares predicted demand over the lead-time period against available stock (on_hand + on_order).
       - Daily demand is calculated as weekly demand / 7.
       - Reorder point is calculated as avg_daily_demand * (lead_time_days + safety_stock_days).
       - Stockout risk is 'High' if available stock is less than lead time demand.
       
    2. Overstock Risk:
       - Compares current on-hand stock against predicted demand over a forward window of 6 weeks.
       - Overstock risk is 'High' if current stock exceeds expected demand by overstock_trigger_ratio.
       
    3. Rupee Financial Impact:
       - Sales at Risk = Shortage Units (Lead Time Demand - Available Stock) * Unit Price.
       - Capital Locked = Excess Units (Current Stock - Forward Demand) * Unit Cost.
    """
    safety_stock = RISK_CONFIG["safety_stock_days"]
    overstock_weeks = RISK_CONFIG["overstock_weeks_window"]
    stockout_trigger = RISK_CONFIG["stockout_trigger_ratio"]
    overstock_trigger = RISK_CONFIG["overstock_trigger_ratio"]
    
    summary_rows = []
    
    for sku_id, group in forecast_df.groupby("sku_id"):
        group = group.copy()
        
        # Metadata values
        latest = group.iloc[-1]
        product = latest["product"]
        category = latest["category"]
        subcategory = latest["subcategory"]
        on_hand = float(latest["on_hand_units"])
        on_order = float(latest["on_order_units"])
        lead_time = float(latest["lead_time_days"])
        unit_cost = float(latest["unit_cost"])
        unit_price = float(latest["price"])
        
        # Calculate daily demand rate based on weekly forecast average
        total_forecast_demand = float(group["predicted_demand"].sum())
        horizon_weeks = len(group)
        avg_weekly_demand = total_forecast_demand / horizon_weeks if horizon_weeks > 0 else 0.0
        avg_daily_demand = avg_weekly_demand / 7.0
        
        # 1. Lead Time Demand and Stockout risk evaluation
        lead_time_demand = avg_daily_demand * lead_time
        available_inventory = on_hand + on_order
        reorder_point = int(np.ceil(avg_daily_demand * (lead_time + safety_stock)))
        
        # Stockout Risk Score = Ratio of lead time demand to available inventory
        if lead_time_demand > 0:
            stockout_score = max(0.0, min(1.0, 1.0 - (available_inventory / lead_time_demand)))
        else:
            stockout_score = 0.0
            
        stockout_risk_level = "High" if available_inventory < (lead_time_demand * stockout_trigger) else "Low"
        
        # 2. Forward Window Demand and Overstock evaluation
        # Zidio overstock checks expected demand over 6 weeks
        expected_forward_demand = avg_weekly_demand * overstock_weeks
        
        if expected_forward_demand > 0:
            overstock_score = max(0.0, on_hand / expected_forward_demand)
        else:
            overstock_score = 0.0
            
        overstock_risk_level = "High" if on_hand > (expected_forward_demand * overstock_trigger) else "Low"
        
        # 3. Replenishment Decision Engine Actions mapping
        if stockout_risk_level == "High" and overstock_risk_level == "Low":
            action = "REORDER NOW"
            recommendation = "Reorder inventory immediately to cover lead time demand"
            priority = "Critical" if on_hand < (avg_daily_demand * 3) else "High"
        elif overstock_risk_level == "High" and stockout_risk_level == "Low":
            action = "MARKDOWN / CLEAR"
            recommendation = "Pause purchasing and run markdown promotions to clear excess inventory"
            priority = "Medium" if on_hand > (expected_forward_demand * 2.0) else "Low"
        elif stockout_risk_level == "High" and overstock_risk_level == "High":
            action = "WATCH / VOLATILE"
            recommendation = "Unstable supply-demand signals. Monitor stock levels closely"
            priority = "High"
        else:
            action = "HEALTHY"
            recommendation = "Inventory levels are stable and within target boundaries"
            priority = "Low"
            
        # 4. Rupee financial impact calculations
        # Sales at Risk = Shortage Units * Price
        shortage_units = max(0.0, lead_time_demand - available_inventory)
        sales_at_risk = round(shortage_units * unit_price, 2)
        
        # Capital Locked = Excess Units * Cost
        excess_units = max(0.0, on_hand - expected_forward_demand)
        capital_locked = round(excess_units * unit_cost, 2)
        
        days_of_cover = on_hand / avg_daily_demand if avg_daily_demand > 0 else 999.0
        recommended_order = max(0, reorder_point - int(available_inventory)) if action == "REORDER NOW" else 0
        
        summary_rows.append({
            "sku": sku_id,
            "sku_id": sku_id,
            "product": product,
            "category": category,
            "subcategory": subcategory,
            "on_hand_units": on_hand,
            "current_stock": on_hand,
            "on_order_units": on_order,
            "lead_time_days": lead_time,
            "reorder_point": reorder_point,
            "forecast_units": total_forecast_demand,
            "avg_daily_demand": avg_daily_demand,
            "days_of_cover": days_of_cover,
            "stockout_score": stockout_score,
            "stockout_risk": stockout_risk_level,
            "overstock_score": overstock_score,
            "overstock_risk": overstock_risk_level,
            "action": action,
            "risk": "Stockout" if stockout_risk_level == "High" else "Overstock" if overstock_risk_level == "High" else "Healthy",
            "priority": priority,
            "recommendation": recommendation,
            "recommended_order": recommended_order,
            "sales_at_risk": sales_at_risk,
            "capital_locked": capital_locked,
            "excess_units": excess_units,
            "unit_price": unit_price,
            "unit_cost": unit_cost
        })
        
    summary = pd.DataFrame(summary_rows)
    priority_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
    return summary.assign(_priority_rank=summary["priority"].map(priority_order)).sort_values(["_priority_rank", "days_of_cover"]).drop(columns="_priority_rank")


def recommendations(risk_df: pd.DataFrame) -> pd.DataFrame:
    """Return action recommendations list matching legacy method signature."""
    return risk_df[[
        "sku", "product", "risk", "priority", "current_stock", 
        "forecast_units", "days_of_cover", "recommended_order", 
        "recommendation", "action", "sales_at_risk", "capital_locked"
    ]]
