"""Project FORESIGHT Entrypoint. Run with: streamlit run app.py"""
from __future__ import annotations

import streamlit as st

from auth.session import init_session
from auth.login import show_login_screen

# Initialize session state variables first
init_session()

# Set initial_sidebar_state dynamically based on auth state
sidebar_state = "expanded" if st.session_state.get("logged_in") else "collapsed"
st.set_page_config(
    page_title="FORESIGHT", 
    page_icon="🔭", 
    layout="wide",
    initial_sidebar_state=sidebar_state
)

# Route dynamically based on authentication state
if not st.session_state.logged_in:
    # Render ONLY the login page with navigation hidden
    login_page = st.Page(show_login_screen, title="Login", icon="🔒")
    pg = st.navigation([login_page], position="hidden")
    pg.run()
else:
    # Import page views lazily ONLY when authenticated
    from pages.Dashboard import show_dashboard, show_business_insights
    from pages.Forecast import show_forecast, show_sku_explorer
    from pages.Risk import show_risk_analysis, show_inventory_health
    from pages.Reports import show_reports
    from pages.Settings import show_settings

    # Role-based pages configuration
    role = st.session_state.role
    
    # Base pages available to everyone (Viewer, Planner, Admin)
    dashboard_page = st.Page(show_dashboard, title="Dashboard", icon="📊", default=True)
    forecast_page = st.Page(show_forecast, title="Forecast", icon="📈")
    reports_page = st.Page(show_reports, title="Reports", icon="📋")
    
    pages = [dashboard_page, forecast_page]
    
    # Roles permissions mapping
    if role in ["Administrator", "Inventory Planner"]:
        risk_page = st.Page(show_risk_analysis, title="Risk Analysis", icon="⚠️")
        health_page = st.Page(show_inventory_health, title="Inventory Health", icon="🏥")
        insights_page = st.Page(show_business_insights, title="Business Insights", icon="💡")
        sku_page = st.Page(show_sku_explorer, title="SKU Explorer", icon="🔍")
        
        pages.extend([risk_page, health_page, insights_page, sku_page])
        
    # Reports is common to all
    pages.append(reports_page)
    
    # Settings only for Admin
    if role == "Administrator":
        settings_page = st.Page(show_settings, title="Settings", icon="⚙️")
        pages.append(settings_page)
        
    pg = st.navigation(pages, position="sidebar")
    pg.run()
