"""Style utilities for Project FORESIGHT dashboard CSS injection."""
from __future__ import annotations

from pathlib import Path
import streamlit as st

def inject_custom_css():
    """Load the custom assets/styles.css file and inject it into the Streamlit app."""
    # Find assets/styles.css relative to root
    root = Path(__file__).resolve().parents[1]
    css_path = root / "assets" / "styles.css"
    
    if css_path.exists():
        try:
            with open(css_path, "r", encoding="utf-8") as f:
                css_content = f.read()
            
            # Hide sidebar completely when logged out
            if not st.session_state.get("logged_in"):
                css_content += """
                
                /* Completely remove sidebar container and collapse button on login page */
                [data-testid="stSidebar"],
                [data-testid="stSidebarCollapseButton"],
                [data-testid="collapsedControl"],
                section[data-testid="stSidebar"] {
                    display: none !important;
                    width: 0px !important;
                    visibility: hidden !important;
                }
                [data-testid="stAppViewContainer"] {
                    margin-left: 0px !important;
                }
                """

            # Remove any Streamlit heading anchor links and hover underline behavior
            css_content += """
            
            /* Disable Streamlit auto-injected heading anchor hyperlinks */
            [data-testid="stHeaderActionElements"],
            a.header-anchor,
            .stMarkdown h1 a, .stMarkdown h2 a, .stMarkdown h3 a,
            [data-testid="stMarkdownContainer"] h1 a,
            [data-testid="stMarkdownContainer"] h2 a {
                display: none !important;
                pointer-events: none !important;
                text-decoration: none !important;
                cursor: default !important;
                color: inherit !important;
            }

            .stMarkdown h1, .stMarkdown h2, .stMarkdown h3,
            [data-testid="stMarkdownContainer"] h1,
            [data-testid="stMarkdownContainer"] h2 {
                text-decoration: none !important;
                cursor: default !important;
            }

            /* Password visibility eye icon natural right edge alignment */
            [data-testid="stTextInput"] button[aria-label*="password"],
            [data-testid="stTextInput"] button[aria-label*="Password"] {
                right: 14px !important;
            }

            /* Full-width Sign In Primary Button matching coral red theme */
            div[data-testid="stElementContainer"]:has(button[key="sign_in_btn"]),
            div[data-testid="stButton"]:has(button[key="sign_in_btn"]),
            button[key="sign_in_btn"],
            button[kind="primary"] {
                width: 100% !important;
                display: block !important;
                background-color: #FF4B4B !important;
                background-image: linear-gradient(135deg, #FF4B4B 0%, #E63939 100%) !important;
                color: #FFFFFF !important;
                font-weight: 600 !important;
                font-size: 1rem !important;
                border: none !important;
                border-radius: 8px !important;
                padding: 0.65rem 1.2rem !important;
                box-shadow: 0 4px 12px rgba(255, 75, 75, 0.25) !important;
                transition: all 0.2s ease !important;
            }
            button[key="sign_in_btn"]:hover,
            button[kind="primary"]:hover {
                background-color: #E63939 !important;
                box-shadow: 0 6px 16px rgba(255, 75, 75, 0.35) !important;
                transform: translateY(-1px) !important;
            }

            /* Secondary Register Button matching dark outlined theme */
            button[key="switch_register_btn"],
            button[kind="secondary"] {
                background-color: rgba(255, 255, 255, 0.02) !important;
                border: 1px solid rgba(255, 255, 255, 0.2) !important;
                color: #F3F4F6 !important;
                font-weight: 600 !important;
                border-radius: 8px !important;
                padding: 0.45rem 1rem !important;
            }
            button[key="switch_register_btn"]:hover,
            button[kind="secondary"]:hover {
                background-color: rgba(255, 255, 255, 0.08) !important;
                border-color: rgba(255, 255, 255, 0.35) !important;
                color: #FFFFFF !important;
            }

            /* Red/Coral Checked Checkbox state */
            [data-testid="stCheckbox"] input:checked + div,
            [data-testid="stCheckbox"] div[aria-checked="true"] {
                background-color: #FF4B4B !important;
                border-color: #FF4B4B !important;
            }

            /* Remember Me / Forgot Password row flexbox styling */
            [data-testid="stHorizontalBlock"]:has([data-testid="stCheckbox"]):has(button[key="forgot_pass_btn"]) {
                display: flex !important;
                justify-content: space-between !important;
                align-items: center !important;
                width: 100% !important;
                margin: 0 !important;
                padding: 0 !important;
            }

            [data-testid="stHorizontalBlock"]:has([data-testid="stCheckbox"]):has(button[key="forgot_pass_btn"]) > div[data-testid="stColumn"]:nth-of-type(1) {
                padding-left: 0 !important;
                margin-left: 0 !important;
            }

            [data-testid="stHorizontalBlock"]:has([data-testid="stCheckbox"]):has(button[key="forgot_pass_btn"]) > div[data-testid="stColumn"]:nth-of-type(2) {
                display: flex !important;
                justify-content: flex-end !important;
                align-items: center !important;
                padding-right: 0 !important;
                margin-right: 0 !important;
            }

            button[key="forgot_pass_btn"] {
                margin: 0 0 0 auto !important;
                padding: 0 !important;
                display: inline-flex !important;
                justify-content: flex-end !important;
                align-items: center !important;
                text-align: right !important;
                white-space: nowrap !important;
                width: auto !important;
                color: #D1D5DB !important;
                background: transparent !important;
                border: none !important;
                box-shadow: none !important;
            }

            button[key="forgot_pass_btn"]:hover {
                color: #FFFFFF !important;
                background: transparent !important;
            }

            button[key="forgot_pass_btn"] p,
            button[key="forgot_pass_btn"] span {
                text-align: right !important;
                white-space: nowrap !important;
                margin: 0 !important;
                padding: 0 !important;
            }
            """

            st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
        except Exception as e:
            st.warning(f"Failed to load CSS file: {e}")
    else:
        # Fallback inline basic styling if file is not found
        st.markdown(
            """
            <style>
            html, body, [data-testid="stAppViewContainer"] {
                background-color: #0B1220 !important;
                color: #F3F4F6 !important;
            }
            </style>
            """,
            unsafe_allow_html=True
        )
