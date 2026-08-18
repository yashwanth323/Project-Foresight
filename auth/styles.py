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
