"""Forecast and SKU Explorer views for Project FORESIGHT."""
from __future__ import annotations

import streamlit as st
import plotly.express as px
import pandas as pd

from auth.session import init_session, load_data, render_header
from auth.styles import inject_custom_css
from pages.Dashboard import apply_filters
from src.forecast import seasonal_naive_forecast


def show_forecast():
    """Render the main Demand Forecasting view comparing actuals, baseline, and model forecasts."""
    init_session()
    if not st.session_state.get("logged_in"):
        st.warning("Please log in to access this page.")
        st.stop()

    inject_custom_css()
    render_header()
    load_data()

    # Retrieve data
    clean = st.session_state.clean_data
    forecast = st.session_state.forecast_data
    risks = st.session_state.risk_data
    comp_metrics = st.session_state.comparison_metrics

    # Apply global sidebar filters
    clean_f, forecast_f, risks_f = apply_filters(clean, forecast, risks)

    # Empty State check
    if forecast_f.empty:
        st.warning("⚠️ No forecasting data available matching the selected filters. Please adjust your selections in the sidebar.")
        st.stop()

    st.title("🔭 Demand Forecasting")
    st.caption("AI-powered weekly SKU-level demand projections and baseline model comparisons.")

    # Model configuration summary
    selected_model_name = comp_metrics.get("selected_model", "Random Forest") if comp_metrics else "Random Forest"
    selected_model_wape = comp_metrics.get("selected_wape", 0.0) if comp_metrics else 0.0
    
    st.info(
        f"🎯 **Forecasting Engine Status:** The system automatically selected the **{selected_model_name}** model "
        f"since it achieved the lowest out-of-sample backtesting WAPE of **{selected_model_wape:.1%}**."
    )

    # Multiselect SKU filter (within filtered set)
    skus_available = sorted(forecast_f["sku_id"].unique())
    selected_plot_skus = st.multiselect("Select SKUs to plot timeline comparison", skus_available, default=skus_available[:3])

    if not selected_plot_skus:
        st.warning("Please select at least one SKU to view forecasts.")
    else:
        # Filter data for selected SKUs
        plot_forecast = forecast_f[forecast_f["sku_id"].isin(selected_plot_skus)]
        plot_clean = clean_f[clean_f["sku_id"].isin(selected_plot_skus)]
        
        # Calculate Seasonal-Naive Baseline forecast for these SKUs to compare
        seasonal_period = comp_metrics.get("seasonal_period_weeks", 4) if comp_metrics else 4
        baseline_fc = seasonal_naive_forecast(plot_clean, horizon_weeks=4, seasonal_period_weeks=seasonal_period)
        
        # Combine actuals, baseline, and model forecasts
        hist_part = plot_clean[["date", "sku_id", "product", "units_sold"]].copy().rename(columns={"units_sold": "Units"})
        hist_part["Series"] = "Historical Actuals"
        
        baseline_part = baseline_fc[["date", "sku_id", "product", "predicted_demand"]].copy().rename(columns={"predicted_demand": "Units"})
        baseline_part["Series"] = f"Seasonal Naive Baseline (T-{seasonal_period}W)"
        
        model_part = plot_forecast[["date", "sku_id", "product", "predicted_demand"]].copy().rename(columns={"predicted_demand": "Units"})
        model_part["Series"] = f"Forecast ({selected_model_name})"
        
        combined_df = pd.concat([hist_part, baseline_part, model_part]).sort_values("date")
        # Keep last 12 weeks of history + forecast for chart readability
        max_date = combined_df["date"].max()
        combined_df = combined_df[combined_df["date"] >= (max_date - pd.Timedelta(weeks=12))]
        
        fig = px.line(
            combined_df, 
            x="date", 
            y="Units", 
            color="product", 
            line_dash="Series",
            markers=True, 
            title="Actuals vs. Baseline vs. Forecast Projections",
            labels={"Units": "Units", "date": "Week Commencing"}
        )
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#FFFFFF",
            height=400,
            margin=dict(l=20, r=20, t=40, b=20),
            xaxis=dict(showgrid=False),
            yaxis=dict(gridcolor="rgba(255,255,255,0.05)")
        )
        st.plotly_chart(fig, width="stretch")

        # Build registry display list dynamically based on present columns
        registry_cols = ["date", "sku_id", "product", "predicted_demand", "price", "current_stock"]
        registry_names = ["Week Commencing", "SKU ID", "Product Name", "Forecasted Demand (Units)", "Unit Price (₹)", "Current Stock"]
        registry_formats = {
            "Forecasted Demand (Units)": "{:,.0f}",
            "Unit Price (₹)": "₹{:,.2f}",
            "Current Stock": "{:,.0f}"
        }
        
        # Add diagnostic columns if they exist
        if "lag_1" in plot_forecast.columns:
            registry_cols.append("lag_1")
            registry_names.append("Lag 1-Week Sales")
            registry_formats["Lag 1-Week Sales"] = "{:,.0f}"
        if "rolling_mean_7" in plot_forecast.columns:
            registry_cols.append("rolling_mean_7")
            registry_names.append("Rolling 7-Week Mean")
            registry_formats["Rolling 7-Week Mean"] = "{:,.2f}"
            
        display_df = plot_forecast[registry_cols].copy()
        display_df.columns = registry_names
        
        st.dataframe(
            display_df.style.format(registry_formats),
            width="stretch",
            hide_index=True
        )


def show_sku_explorer():
    """Render a deep-dive analysis dashboard for a single selected SKU."""
    init_session()
    if not st.session_state.get("logged_in"):
        st.warning("Please log in to access this page.")
        st.stop()

    if st.session_state.role not in ["Administrator", "Inventory Planner"]:
        st.error("Access Denied: You do not have permission to view SKU Explorer.")
        st.stop()

    inject_custom_css()
    render_header()
    load_data()

    clean = st.session_state.clean_data
    forecast = st.session_state.forecast_data
    risks = st.session_state.risk_data
    comp_metrics = st.session_state.comparison_metrics

    # Sidebar global filters
    clean_f, forecast_f, risks_f = apply_filters(clean, forecast, risks)

    # Empty State check
    if risks_f.empty:
        st.warning("⚠️ No data available matching the selected filters. Please adjust your selections in the sidebar.")
        st.stop()

    st.title("🔍 SKU Explorer")
    st.caption("Drill-down inventory telemetry, cost indicators, and risk analysis for individual SKUs.")

    sku_options = sorted(risks_f["sku_id"].unique())
    selected_sku = st.selectbox("Select SKU code to inspect", sku_options)
    
    if selected_sku:
        sku_risk = risks_f[risks_f["sku_id"] == selected_sku].iloc[0]
        sku_clean = clean_f[clean_f["sku_id"] == selected_sku]
        sku_forecast = forecast_f[forecast_f["sku_id"] == selected_sku]
        
        st.subheader(f"SKU Profile: {sku_risk['product']}")
        
        # Category details
        st.markdown(f"**Category:** `{sku_risk['category']}` | **Subcategory:** `{sku_risk['subcategory']}`")
        
        # Financial margins card
        st.markdown(
            f"""
            <div style="background-color: var(--bg-card); border: 1px solid var(--border-color); padding: 1rem 1.5rem; border-radius: 8px; margin-bottom: 1.5rem;">
                <span style="color:var(--text-muted); font-size:0.85rem; font-weight:600; text-transform:uppercase;">Financial Telemetry</span>
                <div style="display:flex; gap:3rem; margin-top:8px;">
                    <div>Cost: <strong style="color:#FFFFFF; font-size:1.1rem;">₹{sku_risk['unit_cost']:.2f}</strong></div>
                    <div>Price: <strong style="color:#FFFFFF; font-size:1.1rem;">₹{sku_risk['unit_price']:.2f}</strong></div>
                    <div>Margin: <strong style="color:#10B981; font-size:1.1rem;">₹{sku_risk['unit_price'] - sku_risk['unit_cost']:.2f} ({(sku_risk['unit_price'] - sku_risk['unit_cost']) / sku_risk['unit_price']:.1%})</strong></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        # KPI Row
        d1, d2, d3, d4 = st.columns(4)
        with d1:
            st.metric("Current Stock (On-Hand)", f"{int(sku_risk['on_hand_units']):,}", "units")
        with d2:
            st.metric("On-Order Stock", f"{int(sku_risk['on_order_units']):,}", f"Lead time: {int(sku_risk['lead_time_days'])} days")
        with d3:
            st.metric("Days of Coverage", f"{sku_risk['days_of_cover']:.1f}", "days")
        with d4:
            st.metric("Reorder Point (ROP)", f"{int(sku_risk['reorder_point']):,}", "units")
            
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Risk & Action Card
        action_class = "#EF4444" if sku_risk["action"] == "REORDER NOW" else "#F59E0B" if sku_risk["action"] == "MARKDOWN / CLEAR" else "#10B981"
        st.markdown(
            f"""
            <div style="background-color: var(--bg-card); border: 1px solid var(--border-color); padding: 1.5rem; border-radius: 10px;">
                <h4 style="margin-top:0; margin-bottom:10px;">Action Recommendation & Financial Impact</h4>
                <p style="margin: 0; font-size: 1.1rem;">
                    Recommendation: <strong style="color: {action_class};">{sku_risk['action']}</strong>
                </p>
                <p style="margin: 6px 0 0 0; color:var(--text-muted);">
                    {sku_risk['recommendation']}
                </p>
                <div style="display:flex; gap:3rem; margin-top:15px; border-top: 1px solid rgba(255,255,255,0.06); padding-top:15px;">
                    <div>Sales at Risk: <strong style="color:#EF4444; font-size:1.2rem;">₹{sku_risk['sales_at_risk']:,.2f}</strong></div>
                    <div>Capital Locked in Overstock: <strong style="color:#F59E0B; font-size:1.2rem;">₹{sku_risk['capital_locked']:,.2f}</strong></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        # Single SKU Timeline comparison plot
        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("Historical vs. Baseline vs. Model Timeline")
        
        seasonal_period = comp_metrics.get("seasonal_period_weeks", 4) if comp_metrics else 4
        baseline_fc = seasonal_naive_forecast(sku_clean, horizon_weeks=4, seasonal_period_weeks=seasonal_period)
        
        hist_p = sku_clean[["date", "units_sold"]].copy().rename(columns={"units_sold": "Units"})
        hist_p["Series"] = "Historical Actuals"
        
        base_p = baseline_fc[["date", "predicted_demand"]].copy().rename(columns={"predicted_demand": "Units"})
        base_p["Series"] = "Seasonal Naive Baseline"
        
        model_name = comp_metrics.get("selected_model", "Random Forest") if comp_metrics else "Random Forest"
        model_p = sku_forecast[["date", "predicted_demand"]].copy().rename(columns={"predicted_demand": "Units"})
        model_p["Series"] = f"Forecast ({model_name})"
        
        combined_sku = pd.concat([hist_p, base_p, model_p]).sort_values("date")
        combined_sku = combined_sku[combined_sku["date"] >= (combined_sku["date"].max() - pd.Timedelta(weeks=12))]
        
        fig_sku = px.line(
            combined_sku, x="date", y="Units", color="Series",
            line_dash="Series",
            markers=True,
            title=f"{sku_risk['product']} ({selected_sku}) - Daily Timeline Comparison",
            color_discrete_map={"Historical Actuals": "#3B82F6", "Seasonal Naive Baseline": "#9CA3AF", f"Forecast ({model_name})": "#7C3AED"}
        )
        fig_sku.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#FFFFFF",
            height=360,
            margin=dict(l=20, r=20, t=40, b=20),
            xaxis=dict(showgrid=False),
            yaxis=dict(gridcolor="rgba(255,255,255,0.05)")
        )
        st.plotly_chart(fig_sku, width="stretch")


# Support script execution directly
if __name__ == "__main__":
    show_forecast()
