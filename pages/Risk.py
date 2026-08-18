"""Risk Analysis and Inventory Health views for Project FORESIGHT."""
from __future__ import annotations

import streamlit as st
import plotly.express as px
import pandas as pd

from auth.session import init_session, load_data, render_header
from auth.styles import inject_custom_css
from pages.Dashboard import apply_filters
from src.risk import recommendations, RISK_CONFIG


def verify_access():
    """Verify that the logged-in user has permission for risk views."""
    init_session()
    if not st.session_state.get("logged_in"):
        st.warning("Please log in to access this page.")
        st.stop()
    if st.session_state.role not in ["Administrator", "Inventory Planner"]:
        st.error("Access Denied: You do not have permission to view this resource.")
        st.stop()


def get_risk_data():
    """Ensure data is loaded and return risk details."""
    load_data()
    return st.session_state.risk_data


def show_risk_analysis():
    """Render the Risk Analysis dashboard page."""
    verify_access()
    inject_custom_css()
    render_header()
    
    clean = st.session_state.clean_data
    forecast = st.session_state.forecast_data
    risks = get_risk_data()
    
    # Apply global filters in the sidebar
    _, _, risks_f = apply_filters(clean, forecast, risks)
    
    # Empty State check
    if risks_f.empty:
        st.warning("⚠️ No risk registry data available matching the selected filters. Please adjust your selections in the sidebar.")
        st.stop()
        
    st.title("⚠️ Risk Analysis")
    st.caption("Identify stockout and overstock exceptions across active SKUs.")
    
    # Risk registers and priority counts
    col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
    stockouts = risks_f[risks_f["action"] == "REORDER NOW"]
    overstock = risks_f[risks_f["action"] == "MARKDOWN / CLEAR"]
    healthy = risks_f[risks_f["action"] == "HEALTHY"]
    
    with col_kpi1:
        st.metric("Stockout Risk SKUs (Reorder)", len(stockouts), delta_color="inverse")
    with col_kpi2:
        st.metric("Overstock Risk SKUs (Markdown)", len(overstock))
    with col_kpi3:
        st.metric("Healthy SKUs", len(healthy))
        
    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("Filter Risk Registry")
    
    # Table representation of risk register
    st.dataframe(
        risks_f[["sku", "product", "category", "action", "priority", "on_hand_units", "days_of_cover", "sales_at_risk", "capital_locked"]].style.format({
            "on_hand_units": "{:,.0f}",
            "days_of_cover": "{:.1f}",
            "sales_at_risk": "₹{:,.2f}",
            "capital_locked": "₹{:,.2f}"
        }),
        width="stretch",
        hide_index=True
    )
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Priority Distribution Chart
    st.subheader("Priority Distribution")
    priority_counts = risks_f["priority"].value_counts().reset_index()
    priority_counts.columns = ["Priority", "Count"]
    
    priority_colors = {
        "Critical": "#EF4444", # danger
        "High": "#F59E0B",     # warning
        "Medium": "#6366F1",   # purple/indigo
        "Low": "#10B981"       # success
    }
    
    fig_priority = px.bar(
        priority_counts, x="Priority", y="Count",
        color="Priority",
        color_discrete_map=priority_colors,
        title="Active Risk Priority Count"
    )
    fig_priority.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="#FFFFFF",
        height=320,
        margin=dict(l=20, r=20, t=40, b=20),
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor="rgba(255,255,255,0.05)")
    )
    st.plotly_chart(fig_priority, width="stretch")


def show_inventory_health():
    """Render the Inventory Health dashboard page."""
    verify_access()
    inject_custom_css()
    render_header()
    
    clean = st.session_state.clean_data
    forecast = st.session_state.forecast_data
    risks = get_risk_data()
    
    # Apply global filters in the sidebar
    _, _, risks_f = apply_filters(clean, forecast, risks)
    
    # Empty State check
    if risks_f.empty:
        st.warning("⚠️ No inventory health data available matching the selected filters. Please adjust your selections in the sidebar.")
        st.stop()
        
    action_df = recommendations(risks_f)
    
    st.title("🏥 Inventory Health")
    st.caption("Replenishment recommendations and stock allocation details.")
    
    st.subheader("Replenishment Recommendations & Actions")
    
    # Warnings container
    non_healthy = risks_f[risks_f["action"] != "HEALTHY"]
    if not non_healthy.empty:
        for _, row in non_healthy.iterrows():
            if row["action"] == "REORDER NOW":
                rec_icon = "🚨"
                alert_func = st.error
            elif row["action"] == "MARKDOWN / CLEAR":
                rec_icon = "🏷️"
                alert_func = st.warning
            else:
                rec_icon = "👀"
                alert_func = st.info
                
            alert_func(
                f"{rec_icon} **{row['product']} ({row['sku']})** | **{row['action']} Recommendation** "
                f"({row['days_of_cover']:.1f} days cover)\n\n"
                f"* **Action Required:** {row['recommendation']}\n"
                f"* **Current Stock:** {int(row['on_hand_units'])} units | **Reorder Point:** {int(row['reorder_point'])} units | "
                f"**Suggested Order:** **{int(row['recommended_order'])} units**"
            )
    else:
        st.success("✅ All selected SKUs have healthy inventory levels. No replenishment actions required.")
        
    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("Stock Level vs. Reorder Point (ROP)")
    
    # Bar Chart: Stock vs Reorder Point
    fig_health = px.bar(
        risks_f, 
        x="product", 
        y=["on_hand_units", "reorder_point"],
        barmode="group",
        title="Current On-Hand Stock vs. Calculated Reorder Point",
        labels={"value": "Units", "variable": "Metric", "product": "Product"}
    )
    fig_health.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="#FFFFFF",
        height=360,
        margin=dict(l=20, r=20, t=40, b=20),
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor="rgba(255,255,255,0.05)")
    )
    st.plotly_chart(fig_health, width="stretch")
    
    # Central Config Threshold Info box
    st.info(
        f"⚙️ **Central Risk Configuration:**\n\n"
        f"* **ROP Calculation:** `Daily Demand * (Lead Time Days + {RISK_CONFIG['safety_stock_days']} Days Safety Stock)`\n"
        f"* **Overstock Trigger:** Stock exceeding **{RISK_CONFIG['overstock_trigger_ratio']}x** expected demand over a **{RISK_CONFIG['overstock_weeks_window']}-week** forward window.\n"
        f"* **Stockout Trigger:** Stock below **{RISK_CONFIG['stockout_trigger_ratio']}x** lead time demand."
    )


# Executed when loaded as script directly
if __name__ == "__main__":
    show_risk_analysis()
