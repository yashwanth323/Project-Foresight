"""Reports view for Project FORESIGHT."""
from __future__ import annotations

import streamlit as st
import pandas as pd
import io

from auth.session import init_session, load_data, render_header
from auth.styles import inject_custom_css
from pages.Dashboard import apply_filters


def show_reports():
    """Render the Reports page view."""
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

    # Apply global sidebar filters
    clean_f, forecast_f, risks_f = apply_filters(clean, forecast, risks)

    # Empty State check
    if risks_f.empty:
        st.warning("⚠️ No report data available matching the selected filters. Please adjust your selections in the sidebar.")
        st.stop()

    st.title("📋 Reports & Exports")
    st.caption("Generate, view, and export inventory health reports and summaries.")

    st.subheader("Inventory Action Registry Report")

    # Display table of filtered recommendations
    report_df = risks_f[[
        "sku", "product", "category", "action", "priority", 
        "on_hand_units", "days_of_cover", "recommended_order", 
        "sales_at_risk", "capital_locked"
    ]].copy()
    
    st.dataframe(
        report_df.style.format({
            "on_hand_units": "{:,.0f}",
            "days_of_cover": "{:.1f}",
            "recommended_order": "{:,.0f}",
            "sales_at_risk": "₹{:,.2f}",
            "capital_locked": "₹{:,.2f}"
        }),
        width="stretch",
        hide_index=True
    )

    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("Export Options")

    col_csv, col_xlsx = st.columns(2)

    with col_csv:
        # Generate CSV in memory
        csv_buffer = io.StringIO()
        report_df.to_csv(csv_buffer, index=False)
        csv_bytes = csv_buffer.getvalue().encode('utf-8')
        
        st.download_button(
            label="Download Report as CSV",
            data=csv_bytes,
            file_name="foresight_inventory_report.csv",
            mime="text/csv",
            width="stretch",
            type="primary"
        )

    with col_xlsx:
        # Generate Excel in memory
        excel_buffer = io.BytesIO()
        try:
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                report_df.to_excel(writer, index=False, sheet_name="Inventory Report")
            excel_bytes = excel_buffer.getvalue()
            
            st.download_button(
                label="Download Report as Excel (XLSX)",
                data=excel_bytes,
                file_name="foresight_inventory_report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width="stretch"
            )
        except Exception as e:
            st.error(f"Excel export unavailable: {e}. Please ensure 'openpyxl' is installed.")

    # Quick stats summary section
    st.markdown("<br><hr style='border-color: rgba(255,255,255,0.08); margin: 1.5rem 0;'>", unsafe_allow_html=True)
    st.subheader("Report Statistics Summary")

    total_skus = len(risks_f)
    stockouts_count = len(risks_f[risks_f["action"] == "REORDER NOW"])
    overstocks_count = len(risks_f[risks_f["action"] == "MARKDOWN / CLEAR"])
    healthy_count = len(risks_f[risks_f["action"] == "HEALTHY"])

    s1, s2, s3 = st.columns(3)
    with s1:
        st.markdown(
            f"""
            <div style="background-color: var(--bg-card); padding: 1.25rem; border-radius: 8px; border: 1px solid var(--border-color); text-align: center;">
                <div style="font-size: 0.85rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase;">Stockout Risk Ratio</div>
                <div style="font-size: 2rem; font-weight: 700; color: #EF4444; margin-top: 5px;">
                    {stockouts_count / total_skus:.1%}
                </div>
                <div style="font-size: 0.8rem; color: var(--text-muted); margin-top: 5px;">{stockouts_count} of {total_skus} SKUs</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with s2:
        st.markdown(
            f"""
            <div style="background-color: var(--bg-card); padding: 1.25rem; border-radius: 8px; border: 1px solid var(--border-color); text-align: center;">
                <div style="font-size: 0.85rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase;">Overstock Risk Ratio</div>
                <div style="font-size: 2rem; font-weight: 700; color: #F59E0B; margin-top: 5px;">
                    {overstocks_count / total_skus:.1%}
                </div>
                <div style="font-size: 0.8rem; color: var(--text-muted); margin-top: 5px;">{overstocks_count} of {total_skus} SKUs</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with s3:
        st.markdown(
            f"""
            <div style="background-color: var(--bg-card); padding: 1.25rem; border-radius: 8px; border: 1px solid var(--border-color); text-align: center;">
                <div style="font-size: 0.85rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase;">Healthy Stock Ratio</div>
                <div style="font-size: 2rem; font-weight: 700; color: #10B981; margin-top: 5px;">
                    {healthy_count / total_skus:.1%}
                </div>
                <div style="font-size: 0.8rem; color: var(--text-muted); margin-top: 5px;">{healthy_count} of {total_skus} SKUs</div>
            </div>
            """,
            unsafe_allow_html=True
        )


# Support script execution directly
if __name__ == "__main__":
    show_reports()
