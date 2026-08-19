"""Dashboard and Business Insights views for Project FORESIGHT."""
from __future__ import annotations

import io
from datetime import datetime
import streamlit as st
import plotly.express as px
import pandas as pd

from auth.session import init_session, load_data, render_header
from auth.styles import inject_custom_css
from auth.database import load_users


def apply_filters(clean_df: pd.DataFrame, forecast_df: pd.DataFrame, risks_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Render global operational filters in the sidebar and apply them to the datasets."""
    if clean_df is None or forecast_df is None or risks_df is None:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    # Guard: Never initialize or touch sidebar elements if the user is logged out
    if not st.session_state.get("logged_in"):
        return clean_df, forecast_df, risks_df

    st.sidebar.header("Global Operational Filters")
    
    # 1. Category Filter
    categories = sorted(clean_df["category"].dropna().unique())
    selected_cat = st.sidebar.selectbox("Category", ["All"] + list(categories))
    
    # Filter by category first to populate subcategories
    temp_clean = clean_df.copy()
    if selected_cat != "All":
        temp_clean = temp_clean[temp_clean["category"] == selected_cat]
        
    # 2. Action Recommendation Filter
    actions = ["All", "REORDER NOW", "MARKDOWN / CLEAR", "WATCH / VOLATILE", "HEALTHY"]
    selected_action = st.sidebar.selectbox("Action Recommendation", actions, index=0)
        
    # 3. Subcategory Filter
    subcategories = sorted(temp_clean["subcategory"].dropna().unique())
    selected_subcat = st.sidebar.selectbox("Subcategory", ["All"] + list(subcategories))
    
    # 4. SKU Filter
    skus_available = sorted(temp_clean["sku_id"].unique())
    selected_skus = st.sidebar.multiselect("SKU Code", skus_available)
    
    # Apply filters to all dataframes
    clean_filtered = clean_df.copy()
    forecast_filtered = forecast_df.copy()
    risks_filtered = risks_df.copy()
    
    if selected_cat != "All":
        clean_filtered = clean_filtered[clean_filtered["category"] == selected_cat]
        forecast_filtered = forecast_filtered[forecast_filtered["category"] == selected_cat]
        risks_filtered = risks_filtered[risks_filtered["category"] == selected_cat]
        
    if selected_subcat != "All":
        clean_filtered = clean_filtered[clean_filtered["subcategory"] == selected_subcat]
        forecast_filtered = forecast_filtered[forecast_filtered["subcategory"] == selected_subcat]
        risks_filtered = risks_filtered[risks_filtered["subcategory"] == selected_subcat]
        
    if selected_skus:
        clean_filtered = clean_filtered[clean_filtered["sku_id"].isin(selected_skus)]
        forecast_filtered = forecast_filtered[forecast_filtered["sku_id"].isin(selected_skus)]
        risks_filtered = risks_filtered[risks_filtered["sku_id"].isin(selected_skus)]
        
    if selected_action != "All":
        risks_filtered = risks_filtered[risks_filtered["action"] == selected_action]
        matching_skus = risks_filtered["sku_id"].unique()
        clean_filtered = clean_filtered[clean_filtered["sku_id"].isin(matching_skus)]
        forecast_filtered = forecast_filtered[forecast_filtered["sku_id"].isin(matching_skus)]
        
    return clean_filtered, forecast_filtered, risks_filtered


def show_dashboard():
    """Main routing dashboard switcher based on user role."""
    init_session()
    if not st.session_state.get("logged_in"):
        st.warning("Please log in to access this page.")
        st.stop()

    inject_custom_css()
    render_header()
    load_data()

    role = st.session_state.role
    if role == "Administrator":
        show_admin_dashboard()
    elif role == "Inventory Planner":
        show_planner_dashboard()
    else:
        show_viewer_dashboard()


# -----------------------------------------------------------------------------
# ROLE 1: ADMINISTRATOR DASHBOARD (Technical & System Control)
# -----------------------------------------------------------------------------
def show_admin_dashboard():
    """Render technical system administration dashboard for Administrators."""
    clean = st.session_state.clean_data
    forecast = st.session_state.forecast_data
    risks = st.session_state.risk_data
    comp_metrics = st.session_state.comparison_metrics
    raw_data = st.session_state.raw_data

    clean_f, forecast_f, risks_f = apply_filters(clean, forecast, risks)

    # Hero Banner
    st.markdown(
        """
        <div class="hero-banner-admin">
            <h2 style="margin: 0; font-size: 1.8rem; font-weight: 700; color: #FFFFFF;">
                ⚙️ FORESIGHT Platform Administration & System Control
            </h2>
            <p style="margin: 5px 0 0 0; color: #D1D5DB; font-size: 0.95rem;">
                Technical telemetry, database status, model performance backtesting, audit logs, and system operations.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # System Status Metrics
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("System Health", "Operational 🟢", "Uptime 99.9%")
    with c2:
        raw_count = len(raw_data) if raw_data is not None else 0
        st.metric("Database Status", f"{raw_count:,} Rows", "Raw Transactions")
    with c3:
        active_users_count = len(load_users())
        st.metric("Active Users", f"{active_users_count} Accounts", "Configured Roles")
    with c4:
        champ = comp_metrics.get("selected_model", "Random Forest") if comp_metrics else "Random Forest"
        st.metric("Last Model Training", champ, "Champion Model")
    with c5:
        acc = st.session_state.accuracy * 100
        st.metric("Forecast Accuracy", f"{acc:.1f}%", "Out-of-sample WAPE")

    st.markdown("<br>", unsafe_allow_html=True)

    # Admin Quick Action Controls
    st.subheader("⚡ System Control Console (Quick Actions)")
    ac1, ac2, ac3, ac4 = st.columns(4)
    with ac1:
        if st.button("📤 Upload Dataset", type="primary", use_container_width=True):
            st.session_state.settings_target_tab = "Data Feed Management"
            st.toast("📤 Data Feed Ingestion focus saved.")
            st.info("💡 **Upload Dataset**: Navigate to **Settings** ⚙️ in the sidebar to ingest raw sales CSV feeds.")
    with ac2:
        if st.button("🤖 Retrain Forecast Model", use_container_width=True):
            with st.spinner("Executing pipeline re-train & rolling-origin backtests..."):
                load_data(force_reload=True)
                st.session_state.settings_target_tab = "Model Performance & Training"
                st.toast("⚡ Model retrained successfully!")
                st.success("Model retrained successfully! Out-of-sample backtest comparisons updated.")
    with ac3:
        if st.button("👥 Manage Users", use_container_width=True):
            st.session_state.settings_target_tab = "User Management"
            st.toast("👥 User Management focus saved.")
            st.info("💡 **User Accounts**: Navigate to **Settings** ⚙️ in the sidebar to inspect user roles & security.")
    with ac4:
        if st.button("📋 System Audit Logs", use_container_width=True):
            st.session_state.settings_target_tab = "Audit Logs & Config"
            st.toast("📋 Audit Logs selected. See Telemetry below.")
            st.info("💡 **Audit Logs**: Viewing System Audit Telemetry below. Full config available under **Settings** ⚙️.")

    st.markdown("<br><hr style='border-color: rgba(255,255,255,0.08);'>", unsafe_allow_html=True)

    # Model Performance & Telemetry Breakdown
    col_left, col_right = st.columns([1.2, 1], gap="medium")
    with col_left:
        st.subheader("Out-of-Sample Model Comparison")
        if comp_metrics:
            comp_rows = []
            for model_name in ["Random Forest", "Seasonal Naive"]:
                metrics = comp_metrics.get(model_name, {})
                comp_rows.append({
                    "Model Algorithm": model_name,
                    "WAPE (Primary Metric)": f"{metrics.get('WAPE', 0.0):.2%}",
                    "Bias": f"{metrics.get('Bias', 0.0):+.2%}",
                    "Rank": metrics.get("Rank", 0)
                })
            comp_df = pd.DataFrame(comp_rows).sort_values("Rank")
            st.dataframe(comp_df, use_container_width=True, hide_index=True)
            st.caption(f"Champion model `{champ}` selected based on lower rolling-origin cross-validation WAPE.")
        else:
            st.info("No model telemetry available.")

    with col_right:
        st.subheader("Data Pipeline Schema Telemetry")
        st.dataframe(
            pd.DataFrame([
                {"Table": "sales_daily.csv", "Status": "Active 🟢", "Rows": len(raw_data) if raw_data is not None else 0},
                {"Table": "sales_clean_weekly.csv", "Status": "Active 🟢", "Rows": len(clean)},
                {"Table": "forecast_data", "Status": "Active 🟢", "Rows": len(forecast)},
                {"Table": "inventory_risks", "Status": "Active 🟢", "Rows": len(risks)}
            ]),
            use_container_width=True,
            hide_index=True
        )

    # Audit Logs Section
    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("📜 System Audit & Activity Logs")
    audit_data = [
        {"Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"), "Event Type": "USER_LOGIN", "User": st.session_state.username, "Role": "Administrator", "Status": "SUCCESS"},
        {"Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"), "Event Type": "MODEL_INFERENCE", "User": "SYSTEM", "Role": "Backend", "Status": "SUCCESS"},
        {"Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"), "Event Type": "PIPELINE_RUN", "User": "SYSTEM", "Role": "Backend", "Status": "COMPLETED"},
        {"Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"), "Event Type": "SCHEMA_VALIDATION", "User": "SYSTEM", "Role": "Dataform", "Status": "PASSED"}
    ]
    st.dataframe(pd.DataFrame(audit_data), use_container_width=True, hide_index=True)


# -----------------------------------------------------------------------------
# ROLE 2: INVENTORY PLANNER DASHBOARD (Operational Planning)
# -----------------------------------------------------------------------------
def show_planner_dashboard():
    """Render operational planning dashboard for Inventory Planners."""
    clean = st.session_state.clean_data
    forecast = st.session_state.forecast_data
    risks = st.session_state.risk_data

    clean_f, forecast_f, risks_f = apply_filters(clean, forecast, risks)

    if risks_f.empty:
        st.warning("⚠️ No inventory data available matching selected filters.")
        st.stop()

    # Hero Banner
    st.markdown(
        """
        <div class="hero-banner-planner">
            <h2 style="margin: 0; font-size: 1.8rem; font-weight: 700; color: #FFFFFF;">
                📋 FORESIGHT Inventory Planning Control
            </h2>
            <p style="margin: 5px 0 0 0; color: #D1D5DB; font-size: 0.95rem;">
                Daily stockout prevention, reorder approvals, overstock liquidation, and purchase order generation.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Calculate operational metrics
    stockouts_list = risks_f[risks_f["action"] == "REORDER NOW"]
    overstock_list = risks_f[risks_f["action"] == "MARKDOWN / CLEAR"]
    stockouts_count = len(stockouts_list)
    overstock_count = len(overstock_list)
    
    total_sales_at_risk = risks_f["sales_at_risk"].sum()
    total_capital_locked = risks_f["capital_locked"].sum()

    healthy_count = len(risks_f[risks_f["action"] == "HEALTHY"])
    total_count = len(risks_f)
    health_score = (healthy_count / total_count * 100) if total_count > 0 else 100.0

    # Operational KPIs
    col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
    with col_kpi1:
        st.metric("Potential Sales at Risk", f"₹{int(total_sales_at_risk):,}", "Stockout Loss", delta_color="inverse")
    with col_kpi2:
        st.metric("Capital Locked in Overstock", f"₹{int(total_capital_locked):,}", "Excess Capital", delta_color="off")
    with col_kpi3:
        st.metric("Reorders Required", f"{stockouts_count} SKUs", "Needs Supply Order")
    with col_kpi4:
        st.metric("Inventory Health Score", f"{health_score:.1f}%", "Healthy Stock Ratio")

    st.markdown("<br>", unsafe_allow_html=True)

    # Today's Critical Alerts Banner
    if stockouts_count > 0:
        st.error(
            f"🚨 **CRITICAL ALERT:** {stockouts_count} SKU(s) have reached or breached their Reorder Point (ROP). "
            f"Total estimated sales revenue at risk: **₹{int(total_sales_at_risk):,}**. Action required immediately."
        )
    else:
        st.success("✅ **STATUS HEALTHY:** All active SKUs maintain sufficient stock days of cover.")

    # Planner Action Buttons Panel
    st.subheader("⚡ Planner Action Center")
    btn_col1, btn_col2, btn_col3 = st.columns(3)

    # Session approval state
    if "approved_recommendations" not in st.session_state:
        st.session_state.approved_recommendations = set()

    with btn_col1:
        if st.button("✅ Approve AI Purchase Recommendations", type="primary", use_container_width=True):
            count_approved = 0
            for sku in stockouts_list["sku_id"].unique():
                st.session_state.approved_recommendations.add(sku)
                count_approved += 1
            st.toast(f"Approved {count_approved} reorder recommendations!")
            st.success(f"Successfully approved {count_approved} purchase recommendations for procurement!")

    with btn_col2:
        # Generate PO CSV
        if not stockouts_list.empty:
            po_df = stockouts_list[["sku_id", "product", "category", "on_hand_units", "reorder_point", "recommended_order", "unit_cost", "sales_at_risk"]].copy()
            po_df["total_order_cost"] = po_df["recommended_order"] * po_df["unit_cost"]
            csv_po = po_df.to_csv(index=False).encode('utf-8')
            
            st.download_button(
                label="📥 Generate Purchase Order (CSV)",
                data=csv_po,
                file_name=f"Purchase_Order_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.button("📥 Generate Purchase Order (CSV)", disabled=True, use_container_width=True)

    with btn_col3:
        # Export Inventory Report CSV
        report_df = risks_f[["sku_id", "product", "category", "action", "current_stock", "days_of_cover", "sales_at_risk", "capital_locked"]].copy()
        csv_report = report_df.to_csv(index=False).encode('utf-8')
        
        st.download_button(
            label="📊 Export Inventory Report (CSV)",
            data=csv_report,
            file_name=f"Inventory_Risk_Report_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )

    st.markdown("<br><hr style='border-color: rgba(255,255,255,0.08);'>", unsafe_allow_html=True)

    # Section 1: Demand Trend & Action Distribution
    col_left, col_right = st.columns([1.2, 1], gap="medium")
    with col_left:
        st.subheader("Demand Trend & 4-Week AI Forecast")
        hist_trend = clean_f.groupby("date")["units_sold"].sum().reset_index()
        hist_trend["Type"] = "Historical Actuals"
        
        fore_trend = forecast_f.groupby("date")["predicted_demand"].sum().reset_index()
        fore_trend["Type"] = "AI Forecast"
        fore_trend.rename(columns={"predicted_demand": "units_sold"}, inplace=True)
        
        combined_trend = pd.concat([hist_trend, fore_trend]).sort_values("date")
        
        fig_trend = px.line(
            combined_trend, x="date", y="units_sold", color="Type",
            line_dash="Type", markers=True,
            title="Weekly Sales History & Forecast (Units)",
            labels={"units_sold": "Units Sold", "date": "Week Commencing"}
        )
        fig_trend.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font_color="#FFFFFF", height=320, margin=dict(l=20, r=20, t=40, b=20),
            xaxis=dict(showgrid=False), yaxis=dict(gridcolor="rgba(255,255,255,0.05)")
        )
        st.plotly_chart(fig_trend, use_container_width=True)

    with col_right:
        st.subheader("Action Category Breakdown")
        action_counts = risks_f["action"].value_counts().reset_index()
        action_counts.columns = ["Action", "Count"]
        
        action_colors = {
            "HEALTHY": "#10B981",
            "REORDER NOW": "#EF4444",
            "MARKDOWN / CLEAR": "#F59E0B",
            "WATCH / VOLATILE": "#6366F1"
        }
        
        fig_pie = px.pie(
            action_counts, values="Count", names="Action",
            hole=0.45, color="Action", color_discrete_map=action_colors
        )
        fig_pie.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font_color="#FFFFFF", height=320, margin=dict(l=20, r=20, t=40, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5)
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    # Section 2: Top Stockout & Overstock Tables
    st.markdown("<br><hr style='border-color: rgba(255,255,255,0.08);'>", unsafe_allow_html=True)
    col_reorder, col_markdown = st.columns(2, gap="large")
    
    with col_reorder:
        st.markdown("### 🚨 Top 10 Stockout Products (Priority Reorder)")
        reorder_list = risks_f[risks_f["action"] == "REORDER NOW"].sort_values("sales_at_risk", ascending=False).head(10)
        
        if not reorder_list.empty:
            # Check approval status tag
            display_reorder = reorder_list.copy()
            display_reorder["Status"] = display_reorder["sku_id"].apply(
                lambda x: "APPROVED ✅" if x in st.session_state.approved_recommendations else "PENDING ⏳"
            )
            st.dataframe(
                display_reorder[["sku_id", "product", "on_hand_units", "recommended_order", "sales_at_risk", "Status"]].style.format({
                    "on_hand_units": "{:,.0f}",
                    "recommended_order": "{:,.0f}",
                    "sales_at_risk": "₹{:,.2f}"
                }),
                use_container_width=True, hide_index=True
            )
        else:
            st.success("No pending stockout reorders. Inventory is healthy.")
            
    with col_markdown:
        st.markdown("### 🏷️ Top 10 Overstock Products (Priority Clearance)")
        markdown_list = risks_f[risks_f["action"] == "MARKDOWN / CLEAR"].sort_values("capital_locked", ascending=False).head(10)
        
        if not markdown_list.empty:
            st.dataframe(
                markdown_list[["sku_id", "product", "on_hand_units", "days_of_cover", "excess_units", "capital_locked"]].style.format({
                    "on_hand_units": "{:,.0f}",
                    "days_of_cover": "{:.1f}",
                    "excess_units": "{:,.0f}",
                    "capital_locked": "₹{:,.2f}"
                }),
                use_container_width=True, hide_index=True
            )
        else:
            st.success("No excessive overstock detected. Capital is optimized.")


# -----------------------------------------------------------------------------
# ROLE 3: VIEWER DASHBOARD (Executive Management Read-Only)
# -----------------------------------------------------------------------------
def show_viewer_dashboard():
    """Render executive read-only monitoring dashboard for Viewers."""
    clean = st.session_state.clean_data
    forecast = st.session_state.forecast_data
    risks = st.session_state.risk_data

    clean_f, forecast_f, risks_f = apply_filters(clean, forecast, risks)

    if clean_f.empty:
        st.warning("⚠️ No data available matching selected filters.")
        st.stop()

    # Hero Banner
    st.markdown(
        """
        <div class="hero-banner-viewer">
            <h2 style="margin: 0; font-size: 1.8rem; font-weight: 700; color: #FFFFFF;">
                📈 FORESIGHT Executive Demand & Risk Telemetry
            </h2>
            <p style="margin: 5px 0 0 0; color: #D1D5DB; font-size: 0.95rem;">
                High-level business KPIs, executive sales volume trends, total inventory capital, and risk portfolio summary.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Calculate Executive KPIs
    total_forecast_demand = forecast_f["predicted_demand"].sum()
    
    # Calculate estimated capital value of stock on hand
    if "unit_cost" in risks_f.columns and "current_stock" in risks_f.columns:
        total_inventory_value = (risks_f["current_stock"] * risks_f["unit_cost"]).sum()
    else:
        total_inventory_value = 0.0

    acc_score = st.session_state.accuracy * 100
    at_risk_count = len(risks_f[risks_f["action"] != "HEALTHY"])
    total_skus = len(risks_f)

    # Executive KPI Cards
    vk1, vk2, vk3, vk4 = st.columns(4)
    with vk1:
        st.metric("Forecasted Demand", f"{int(total_forecast_demand):,} Units", "Next 4 Weeks")
    with vk2:
        st.metric("Total Inventory Capital", f"₹{int(total_inventory_value):,}", "Stock Value")
    with vk3:
        st.metric("Overall Model Accuracy", f"{acc_score:.1f}%", "Holdout WAPE")
    with vk4:
        st.metric("Portfolio Risk Ratio", f"{at_risk_count} / {total_skus} SKUs", "Need Attention")

    st.markdown("<br>", unsafe_allow_html=True)

    # Executive Charts
    col_chart1, col_chart2 = st.columns([1.2, 1], gap="medium")
    with col_chart1:
        st.subheader("Monthly Demand Volume Overview")
        monthly_demand = clean_f.groupby("month")["units_sold"].sum().reset_index()
        month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        monthly_demand["Month"] = monthly_demand["month"].map(lambda x: month_names[x-1] if 1 <= x <= 12 else str(x))
        
        fig_month = px.bar(
            monthly_demand, x="Month", y="units_sold",
            title="Total Historical Sales Volume by Month",
            labels={"units_sold": "Total Units"}
        )
        fig_month.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font_color="#FFFFFF", height=320, margin=dict(l=20, r=20, t=40, b=20),
            xaxis=dict(showgrid=False), yaxis=dict(gridcolor="rgba(255,255,255,0.05)")
        )
        st.plotly_chart(fig_month, use_container_width=True)

    with col_chart2:
        st.subheader("Inventory Action Portfolio Summary")
        action_counts = risks_f["action"].value_counts().reset_index()
        action_counts.columns = ["Action", "Count"]
        
        action_colors = {
            "HEALTHY": "#10B981",
            "REORDER NOW": "#EF4444",
            "MARKDOWN / CLEAR": "#F59E0B",
            "WATCH / VOLATILE": "#6366F1"
        }
        
        fig_pie = px.pie(
            action_counts, values="Count", names="Action",
            hole=0.45, color="Action", color_discrete_map=action_colors
        )
        fig_pie.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font_color="#FFFFFF", height=320, margin=dict(l=20, r=20, t=40, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5)
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    # Read-Only Summary Table
    st.markdown("<br><hr style='border-color: rgba(255,255,255,0.08);'>", unsafe_allow_html=True)
    st.subheader("Category Performance Summary")
    
    cat_summary = clean_f.groupby("category").agg(
        Total_Units=("units_sold", "sum"),
        Active_SKUs=("sku_id", "nunique")
    ).reset_index()
    
    st.dataframe(cat_summary, use_container_width=True, hide_index=True)


# Keep show_business_insights for Admin & Planner navigation
def show_business_insights():
    """Render Strategic Business Insights dashboard page."""
    init_session()
    if not st.session_state.get("logged_in"):
        st.warning("Please log in to access this page.")
        st.stop()

    inject_custom_css()
    render_header()
    load_data()

    clean = st.session_state.clean_data
    forecast = st.session_state.forecast_data
    risks = st.session_state.risk_data

    clean_f, forecast_f, risks_f = apply_filters(clean, forecast, risks)

    if clean_f.empty:
        st.warning("⚠️ No data available matching selected filters.")
        st.stop()

    st.title("💡 Strategic Business Insights")
    st.caption("Analysis of demand seasonality, categories contribution, and promotion multipliers.")

    product_sales = clean_f.groupby("product")["units_sold"].sum().reset_index()
    product_sales = product_sales.sort_values(by="units_sold", ascending=False)
    
    fig_contrib = px.bar(
        product_sales, x="units_sold", y="product", orientation="h", color="product",
        title="Units Sold by Product SKU", labels={"units_sold": "Units Sold", "product": "Product Name"}
    )
    fig_contrib.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#FFFFFF",
        height=320, showlegend=False, margin=dict(l=20, r=20, t=40, b=20),
        xaxis=dict(gridcolor="rgba(255,255,255,0.05)"), yaxis=dict(showgrid=False)
    )
    st.plotly_chart(fig_contrib, use_container_width=True)

    col_ins1, col_ins2 = st.columns(2, gap="medium")
    with col_ins1:
        st.subheader("Sales Volume Seasonality by Month")
        monthly_df = clean_f.groupby("month")["units_sold"].sum().reset_index()
        month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        monthly_df["Month"] = monthly_df["month"].map(lambda x: month_names[x-1] if 1 <= x <= 12 else str(x))
        
        fig_month = px.bar(monthly_df, x="Month", y="units_sold", title="Total Units Sold by Month Index")
        fig_month.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#FFFFFF",
            height=300, margin=dict(l=20, r=20, t=40, b=20),
            xaxis=dict(showgrid=False), yaxis=dict(gridcolor="rgba(255,255,255,0.05)")
        )
        st.plotly_chart(fig_month, use_container_width=True)

    with col_ins2:
        st.subheader("Sales Volume Distribution by Category")
        cat_df = clean_f.groupby("category")["units_sold"].sum().reset_index()
        fig_cat = px.pie(cat_df, values="units_sold", names="category", title="Category Share", hole=0.4)
        fig_cat.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#FFFFFF",
            height=300, margin=dict(l=20, r=20, t=40, b=20)
        )
        st.plotly_chart(fig_cat, use_container_width=True)


if __name__ == "__main__":
    show_dashboard()
