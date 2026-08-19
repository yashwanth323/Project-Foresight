"""Splash screen and login views for Project FORESIGHT."""
from __future__ import annotations

import base64
import time
from pathlib import Path
from PIL import Image
import streamlit as st

from auth.authentication import authenticate_user
from auth.session import login_user, init_session
from auth.styles import inject_custom_css


def get_image_base64(img_path: Path) -> str:
    """Read an image file and return its base64 encoding."""
    if img_path.exists():
        try:
            with open(img_path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        except Exception:
            return ""
    return ""


def render_splash_screen():
    """Render a premium full-screen splash screen for 2 seconds."""
    root = Path(__file__).resolve().parents[1]
    logo_path = root / "assets" / "logo.png"
    logo_b64 = get_image_base64(logo_path)
    
    splash_html = f"""
    <div style="
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background: linear-gradient(135deg, #0B1220 0%, #161B33 50%, #0F172A 100%);
        background-size: 400% 400%;
        animation: gradientMove 8s ease infinite;
        z-index: 999999;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        font-family: 'Outfit', -apple-system, sans-serif;
        color: #FFFFFF;
    ">
        <style>
            @keyframes gradientMove {{
                0% {{ background-position: 0% 50%; }}
                50% {{ background-position: 100% 50%; }}
                100% {{ background-position: 0% 50%; }}
            }}
            @keyframes spin {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}
            @keyframes fadeIn {{
                from {{ opacity: 0; transform: scale(0.95); }}
                to {{ opacity: 1; transform: scale(1); }}
            }}
            .splash-card {{
                text-align: center;
                animation: fadeIn 1.2s ease-out;
            }}
            .spinner {{
                border: 3px solid rgba(124, 58, 237, 0.15);
                width: 50px;
                height: 50px;
                border-radius: 50%;
                border-left-color: #7C3AED;
                animation: spin 0.8s linear infinite;
                margin: 24px auto;
                box-shadow: 0 0 15px rgba(124, 58, 237, 0.2);
            }}
            .logo-img {{
                width: 90px;
                height: 90px;
                object-fit: contain;
                margin-bottom: 16px;
                filter: drop-shadow(0 0 15px rgba(124, 58, 237, 0.4));
            }}
        </style>
        <div class="splash-card">
            {f'<img class="logo-img" src="data:image/png;base64,{logo_b64}" />' if logo_b64 else '<div style="font-size: 4rem; margin-bottom: 10px;">🔭</div>'}
            <h1 style="font-size: 3rem; font-weight: 700; margin: 0; letter-spacing: -0.03em; background: linear-gradient(90deg, #FFFFFF 0%, #A78BFA 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">FORESIGHT</h1>
            <p style="font-size: 1.1rem; color: #9CA3AF; margin: 8px 0 0 0; font-weight: 400; letter-spacing: 0.05em; text-transform: uppercase;">AI Powered Demand Forecasting</p>
            <div class="spinner"></div>
        </div>
    </div>
    """
    st.markdown(splash_html, unsafe_allow_html=True)
    time.sleep(2)
    st.session_state.splash_shown = True
    st.rerun()


def show_login_screen():
    """Display the production enterprise login screen."""
    init_session()
    inject_custom_css()
    
    # Check if splash needs to run
    if not st.session_state.get("splash_shown"):
        render_splash_screen()
        return

    # Ensure logout message is cleared
    if "logout_message" in st.session_state:
        st.session_state.logout_message = None

    # Centered layout using balanced column ratio
    col_left, col_center, col_right = st.columns([1, 1.2, 1])
    
    with col_center:
        # 1. Single Parent Centered Composition (Logo -> FORESIGHT -> Subtitle)
        root = Path(__file__).resolve().parents[1]
        logo_path = root / "assets" / "logo.png"
        logo_b64 = get_image_base64(logo_path)
        
        st.markdown(
            f"""
            <div style="width: 100%; max-width: 480px; margin: 0 auto 24px auto; text-align: center; display: flex; flex-direction: column; align-items: center; justify-content: center;">
                {f'<img src="data:image/png;base64,{logo_b64}" style="width: 46px; height: 46px; object-fit: contain; margin-bottom: 12px; filter: drop-shadow(0 0 10px rgba(124, 58, 237, 0.35)); pointer-events: none;" />' if logo_b64 else '<div style="font-size: 2.2rem; margin-bottom: 12px; line-height: 1;">🔭</div>'}
                <div style="font-size: 2.4rem; font-weight: 700; margin: 0; line-height: 1.1; background: linear-gradient(135deg, #FFFFFF 0%, #A78BFA 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: -0.03em; cursor: default; text-decoration: none; user-select: text;">
                    FORESIGHT
                </div>
                <div style="font-size: 0.95rem; color: #9CA3AF; opacity: 0.75; margin-top: 8px; text-transform: uppercase; letter-spacing: 2px; font-weight: 600; cursor: default; text-decoration: none;">
                    Demand & Inventory Intelligence
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        # 2. Production Enterprise Login Card
        with st.container(border=True):
            st.markdown(
                """
                <div style="text-align: center; margin-bottom: 1.25rem; margin-top: 0.25rem;">
                    <div style="font-size: 1.45rem; font-weight: 700; margin: 0; color: #FFFFFF; letter-spacing: -0.02em; cursor: default; text-decoration: none;">Welcome Back</div>
                    <div style="font-size: 0.85rem; color: #9CA3AF; margin-top: 4px; cursor: default;">Sign in to access your FORESIGHT workspace.</div>
                </div>
                """,
                unsafe_allow_html=True
            )
            
            email_or_user = st.text_input("Username or Email", placeholder="Enter your username or email", key="login_email")
            
            show_password = st.checkbox("Show Password", key="show_password_cb")
            pass_type = "default" if show_password else "password"
            password = st.text_input("Password", type=pass_type, placeholder="Enter your password", key="login_password")
            
            c_opt1, c_opt2 = st.columns([1, 1])
            with c_opt1:
                st.checkbox("Remember Me", value=True, key="remember_me")
            with c_opt2:
                st.markdown(
                    "<div style='text-align: right; padding-top: 4px;'><span style='color: #9CA3AF; font-size: 0.82rem; cursor: pointer;'>Forgot Password?</span></div>",
                    unsafe_allow_html=True
                )

            st.markdown("<div style='margin-top: 8px;'></div>", unsafe_allow_html=True)
            login_btn = st.button("Sign In", type="primary", use_container_width=True)
            
            if login_btn:
                user = authenticate_user(email_or_user, password)
                if user:
                    login_user(user["username"], user["email"], user["role"])
                    st.toast(f"Welcome back, {user['username']}! Loading workspace...")
                    st.rerun()
                else:
                    st.error("Invalid username or password. Please try again.")

        # 3. Enterprise Copyright Footer
        st.markdown(
            """
            <div style="text-align: center; margin-top: 1.5rem; color: #6B7280; font-size: 0.78rem; letter-spacing: 0.05em; font-weight: 500; cursor: default;">
                © 2026 Project FORESIGHT | AI-Powered Demand Forecasting & Inventory Intelligence
            </div>
            """,
            unsafe_allow_html=True
        )
