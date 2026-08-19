"""Splash screen, login, registration, and password recovery views for Project FORESIGHT."""
from __future__ import annotations

import base64
import time
from pathlib import Path
import streamlit as st

from auth.authentication import authenticate_user
from auth.database import create_user, update_password, get_user_by_email
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
    """Display the production enterprise login, register, and password reset screens."""
    init_session()
    inject_custom_css()
    
    # Check if splash needs to run
    if not st.session_state.get("splash_shown"):
        render_splash_screen()
        return

    # Ensure logout message is cleared
    if "logout_message" in st.session_state:
        st.session_state.logout_message = None

    # Current view mode ("login", "register", "forgot_password")
    if "auth_mode" not in st.session_state:
        st.session_state.auth_mode = "login"

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

        # Flash messages
        if st.session_state.get("reg_success"):
            st.success(st.session_state.pop("reg_success"))

        # ----------------------------------------------------
        # VIEW 1: SIGN IN PAGE
        # ----------------------------------------------------
        if st.session_state.auth_mode == "login":
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
                
                c_opt1, c_opt2 = st.columns([1, 1], vertical_alignment="center")
                with c_opt1:
                    st.checkbox("Remember Me", value=True, key="remember_me")
                with c_opt2:
                    if st.button("Forgot Password?", key="forgot_pass_btn", type="tertiary", use_container_width=True):
                        st.session_state.auth_mode = "forgot_password"
                        st.rerun()

                st.markdown("<div style='margin-top: 8px;'></div>", unsafe_allow_html=True)
                login_btn = st.button("Sign In", type="primary", use_container_width=True, key="sign_in_btn")
                
                if login_btn:
                    user = authenticate_user(email_or_user, password)
                    if user:
                        login_user(user["username"], user["email"], user["role"])
                        st.toast(f"Welcome back, {user['username']}! Loading workspace...")
                        st.rerun()
                    else:
                        st.error("Invalid username/email or password. Please try again.")

                st.markdown("<hr style='margin: 1.2rem 0; border-color: rgba(255,255,255,0.08);'>", unsafe_allow_html=True)
                
                # Register Switch Button
                col_reg_label, col_reg_btn = st.columns([1.4, 1], vertical_alignment="center")
                with col_reg_label:
                    st.markdown("<span style='color: #9CA3AF; font-size: 0.85rem;'>Don't have an account?</span>", unsafe_allow_html=True)
                with col_reg_btn:
                    if st.button("Register", key="switch_register_btn", type="secondary", use_container_width=True):
                        st.session_state.auth_mode = "register"
                        st.rerun()

        # ----------------------------------------------------
        # VIEW 2: REGISTER PAGE
        # ----------------------------------------------------
        elif st.session_state.auth_mode == "register":
            with st.container(border=True):
                st.markdown(
                    """
                    <div style="text-align: center; margin-bottom: 1.25rem; margin-top: 0.25rem;">
                        <div style="font-size: 1.45rem; font-weight: 700; margin: 0; color: #FFFFFF; letter-spacing: -0.02em; cursor: default;">Create Account</div>
                        <div style="font-size: 0.85rem; color: #9CA3AF; margin-top: 4px; cursor: default;">Register to access your FORESIGHT analytics environment.</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                
                full_name = st.text_input("Full Name", placeholder="e.g. Alex Morgan", key="reg_fullname")
                username = st.text_input("Username", placeholder="e.g. alexmorgan", key="reg_username")
                email = st.text_input("Email Address", placeholder="e.g. alex@company.com", key="reg_email")
                
                show_pass_reg = st.checkbox("Show Password", key="reg_show_pass_cb")
                reg_pass_type = "default" if show_pass_reg else "password"
                password = st.text_input("Password", type=reg_pass_type, placeholder="At least 8 chars (1 upper, 1 lower, 1 digit)", key="reg_password")
                confirm_password = st.text_input("Confirm Password", type=reg_pass_type, placeholder="Re-enter password", key="reg_confirm_password")
                
                # Role Selection: Administrator MUST NOT appear
                role = st.selectbox(
                    "Role Permission",
                    options=["Viewer", "Inventory Planner"],
                    index=0,
                    help="Select your operational role. Administrator role is restricted.",
                    key="reg_role"
                )
                
                terms_accepted = st.checkbox("I agree to Terms & Conditions", key="reg_terms")
                
                st.markdown("<div style='margin-top: 12px;'></div>", unsafe_allow_html=True)
                create_btn = st.button("Create Account", type="primary", use_container_width=True, key="create_acct_btn")
                
                if create_btn:
                    if not full_name:
                        st.error("Full name is required.")
                    elif not username:
                        st.error("Username is required.")
                    elif not email:
                        st.error("Email address is required.")
                    elif password != confirm_password:
                        st.error("Passwords do not match. Please try again.")
                    elif not terms_accepted:
                        st.error("You must accept the Terms & Conditions to create an account.")
                    else:
                        success, msg = create_user(full_name, username, email, password, role)
                        if success:
                            st.session_state.auth_mode = "login"
                            st.session_state.reg_success = msg
                            st.rerun()
                        else:
                            st.error(msg)

                st.markdown("<div style='margin-top: 8px;'></div>", unsafe_allow_html=True)
                if st.button("Back to Login", type="secondary", use_container_width=True, key="back_login_from_reg"):
                    st.session_state.auth_mode = "login"
                    st.rerun()

        # ----------------------------------------------------
        # VIEW 3: FORGOT PASSWORD PAGE
        # ----------------------------------------------------
        elif st.session_state.auth_mode == "forgot_password":
            with st.container(border=True):
                st.markdown(
                    """
                    <div style="text-align: center; margin-bottom: 1.25rem; margin-top: 0.25rem;">
                        <div style="font-size: 1.45rem; font-weight: 700; margin: 0; color: #FFFFFF; letter-spacing: -0.02em; cursor: default;">Reset Password</div>
                        <div style="font-size: 0.85rem; color: #9CA3AF; margin-top: 4px; cursor: default;">Enter your registered account email to update your password.</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                
                reset_email = st.text_input("Account Email", placeholder="e.g. planner@foresight.ai", key="reset_email")
                
                show_pass_reset = st.checkbox("Show Passwords", key="reset_show_pass_cb")
                reset_pass_type = "default" if show_pass_reset else "password"
                new_password = st.text_input("New Password", type=reset_pass_type, placeholder="At least 8 chars (1 upper, 1 lower, 1 digit)", key="reset_new_pass")
                confirm_new_password = st.text_input("Confirm New Password", type=reset_pass_type, placeholder="Re-enter new password", key="reset_confirm_pass")
                
                st.markdown("<div style='margin-top: 12px;'></div>", unsafe_allow_html=True)
                update_btn = st.button("Update Password", type="primary", use_container_width=True, key="update_pass_btn")
                
                if update_btn:
                    if not reset_email:
                        st.error("Please enter your account email address.")
                    elif not new_password:
                        st.error("Please enter a new password.")
                    elif new_password != confirm_new_password:
                        st.error("Passwords do not match. Please try again.")
                    else:
                        success, msg = update_password(reset_email, new_password)
                        if success:
                            st.session_state.auth_mode = "login"
                            st.session_state.reg_success = msg
                            st.rerun()
                        else:
                            st.error(msg)

                st.markdown("<div style='margin-top: 8px;'></div>", unsafe_allow_html=True)
                if st.button("Back to Login", type="secondary", use_container_width=True, key="back_login_from_reset"):
                    st.session_state.auth_mode = "login"
                    st.rerun()

        # 3. Enterprise Copyright Footer
        st.markdown(
            """
            <div style="text-align: center; margin-top: 1.5rem; color: #6B7280; font-size: 0.78rem; letter-spacing: 0.05em; font-weight: 500; cursor: default;">
                © 2026 Project FORESIGHT | AI-Powered Demand Forecasting & Inventory Intelligence
            </div>
            """,
            unsafe_allow_html=True
        )
