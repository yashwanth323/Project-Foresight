"""Session management, pipeline orchestration, and security helper functions for Project FORESIGHT."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import streamlit as st
import pandas as pd
import joblib

from src.forecast import forecast_next_days, train_forecast_model
from src.pipeline import run_pipeline, create_demo_sales, load_data as pipe_load_data
from src.risk import score_inventory_risk, recommendations

ROOT = Path(__file__).resolve().parents[1]

def init_session():
    """Initialize default session state keys if not already present."""
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "username" not in st.session_state:
        st.session_state.username = None
    if "email" not in st.session_state:
        st.session_state.email = None
    if "role" not in st.session_state:
        st.session_state.role = None
    if "login_time" not in st.session_state:
        st.session_state.login_time = None
    if "splash_shown" not in st.session_state:
        st.session_state.splash_shown = False
    if "logout_message" not in st.session_state:
        st.session_state.logout_message = None
    if "profile_picture" not in st.session_state:
        st.session_state.profile_picture = None
        
    # Shared Data cache in session state
    if "raw_data" not in st.session_state:
        st.session_state.raw_data = None
    if "clean_data" not in st.session_state:
        st.session_state.clean_data = None
    if "forecast_data" not in st.session_state:
        st.session_state.forecast_data = None
    if "risk_data" not in st.session_state:
        st.session_state.risk_data = None
    if "accuracy" not in st.session_state:
        st.session_state.accuracy = 0.0
    if "comparison_metrics" not in st.session_state:
        st.session_state.comparison_metrics = None

def load_data(force_reload=False):
    """Run preprocessing, train models, forecast weekly demand, and score inventory risks."""
    init_session()
    if (st.session_state.clean_data is None or 
        st.session_state.forecast_data is None or 
        st.session_state.risk_data is None or 
        force_reload):
        raw_dir = ROOT / "data" / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        processed_weekly = ROOT / "data" / "processed" / "sales_clean_weekly.csv"
        
        # 1. Search for official datasets in raw directory
        # If missing, generate fallback demo tables
        required_raw_files = ["sales_daily.csv", "sku_master.csv", "calendar.csv", "inventory_snapshots.csv"]
        missing_any = any(not (raw_dir / f).exists() for f in required_raw_files)
        
        if missing_any:
            # Check if user uploaded any custom csv named sales_daily, etc.
            # Otherwise generate the demo compatible tables
            create_demo_sales(raw_dir)
            
        # 2. Run ingestion, join, and weekly aggregation pipeline
        try:
            clean = run_pipeline(raw_dir, processed_weekly)
            clean["date"] = pd.to_datetime(clean["date"])
            st.session_state.clean_data = clean
            
            # Save raw daily file reference (useful for daily sales checks)
            st.session_state.raw_data = pd.read_csv(raw_dir / "sales_daily.csv")
            st.session_state.raw_data["date"] = pd.to_datetime(st.session_state.raw_data["date"])
        except Exception as exc:
            st.error(f"Pipeline Execution Failed: {exc}")
            st.stop()
            
        # 3. Model Training & Selection (Seasonal Naive vs Random Forest based on backtest)
        model_path = ROOT / "model.pkl"
        try:
            if force_reload or not model_path.exists():
                _, comp_metrics = train_forecast_model(clean, model_path, seasonal_period_weeks=4)
            else:
                try:
                    artifact = joblib.load(model_path)
                    if isinstance(artifact, dict) and "comparison" in artifact and artifact["comparison"] is not None:
                        comp_metrics = artifact["comparison"]
                    else:
                        _, comp_metrics = train_forecast_model(clean, model_path, seasonal_period_weeks=4)
                except Exception:
                    _, comp_metrics = train_forecast_model(clean, model_path, seasonal_period_weeks=4)
            
            st.session_state.comparison_metrics = comp_metrics
            st.session_state.accuracy = 1.0 - comp_metrics["selected_wape"]
        except Exception as exc:
            st.error(f"Model Training/Selection Failed: {exc}")
            st.stop()
            
        # 4. Weekly Forecasting (horizon = 4 weeks)
        try:
            forecasts = forecast_next_days(clean, model_path, horizon=4)
            forecasts["date"] = pd.to_datetime(forecasts["date"])
            st.session_state.forecast_data = forecasts
        except Exception as exc:
            st.error(f"Weekly Forecasting Failed: {exc}")
            st.stop()
            
        # 5. Score Inventory Risk, Actions, and Financial Rupee Impact
        try:
            risks = score_inventory_risk(forecasts)
            st.session_state.risk_data = risks
        except Exception as exc:
            st.error(f"Risk Scoring Failed: {exc}")
            st.stop()

def login_user(username: str, email: str, role: str, profile_picture: str | None = None):
    """Store user information in session state upon successful login."""
    st.session_state.logged_in = True
    st.session_state.username = username
    st.session_state.email = email
    st.session_state.role = role
    st.session_state.profile_picture = profile_picture
    st.session_state.login_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.logout_message = None
    # Reset data cache to force load on next display
    st.session_state.raw_data = None
    st.session_state.clean_data = None
    st.session_state.forecast_data = None
    st.session_state.risk_data = None
    st.session_state.accuracy = 0.0
    st.session_state.comparison_metrics = None

def logout_user():
    """Clear user session details and trigger navigation refresh."""
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.email = None
    st.session_state.role = None
    st.session_state.profile_picture = None
    st.session_state.login_time = None
    st.session_state.logout_message = "You have been logged out successfully."
    st.session_state.raw_data = None
    st.session_state.clean_data = None
    st.session_state.forecast_data = None
    st.session_state.risk_data = None
    st.session_state.accuracy = 0.0
    st.session_state.comparison_metrics = None
    st.rerun()

def get_role_badge_class(role: str) -> str:
    """Return the CSS class name for a given role badge."""
    if role == "Administrator":
        return "badge-admin"
    elif role == "Inventory Planner":
        return "badge-planner"
    else:
        return "badge-viewer"

def render_header():
    """Render a premium top header with user information and logout button."""
    if not st.session_state.get("logged_in"):
        return

    # Use st.columns for clean layout
    cols = st.columns([3, 1.2, 0.8], vertical_alignment="center")
    
    avatar_char = st.session_state.username[0].upper() if st.session_state.username else "U"
    badge_class = get_role_badge_class(st.session_state.role)
    current_date = datetime.now().strftime("%B %d, %Y")
    profile_pic = st.session_state.get("profile_picture")
    
    # Avatar gradient based on role
    if st.session_state.role == "Administrator":
        avatar_bg = "linear-gradient(135deg, #7C3AED 0%, #C084FC 100%)"
        avatar_glow = "rgba(124, 58, 237, 0.4)"
    elif st.session_state.role == "Inventory Planner":
        avatar_bg = "linear-gradient(135deg, #2563EB 0%, #60A5FA 100%)"
        avatar_glow = "rgba(37, 99, 235, 0.4)"
    else:
        avatar_bg = "linear-gradient(135deg, #059669 0%, #34D399 100%)"
        avatar_glow = "rgba(5, 150, 105, 0.4)"
    
    if profile_pic:
        avatar_html = f'<img src="{profile_pic}" style="width: 38px; height: 38px; border-radius: 50%; object-fit: cover; box-shadow: 0 0 12px {avatar_glow};" />'
    else:
        avatar_html = f'<div class="user-avatar" style="background: {avatar_bg}; box-shadow: 0 0 12px {avatar_glow};">{avatar_char}</div>'

    with cols[0]:
        st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            {avatar_html}
            <div>
                <div style="font-weight: 600; color: #FFFFFF; font-size: 1rem; line-height: 1.2;">{st.session_state.username}</div>
                <span class="role-badge {badge_class}">{st.session_state.role}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    with cols[1]:
        st.markdown(f"""
        <div style="text-align: right; color: var(--text-muted); font-size: 0.85rem; font-weight: 500; padding-right: 10px;">
            📅 {current_date}
        </div>
        """, unsafe_allow_html=True)
        
    with cols[2]:
        if st.button("Logout", key="header_logout_btn", type="secondary", use_container_width=True):
            logout_user()
    
    st.markdown("<hr style='margin-top: 1rem; margin-bottom: 2rem; border-color: rgba(255,255,255,0.08);'>", unsafe_allow_html=True)
