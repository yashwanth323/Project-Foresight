"""OAuth orchestration, callback processing, and role mapping for Project FORESIGHT."""
from __future__ import annotations

from datetime import datetime
import streamlit as st
from auth.google_auth import (
    get_google_auth_url, 
    exchange_code_for_user_info, 
    is_google_oauth_configured
)
from auth.users import load_users


def map_email_to_role(email: str) -> str | None:
    """Map Google user email to role permission."""
    email_clean = email.strip().lower()
    
    # 1. Official default email role mapping
    if email_clean == "admin@foresight.ai":
        return "Administrator"
    elif email_clean == "planner@foresight.ai":
        return "Inventory Planner"
    elif email_clean == "viewer@foresight.ai":
        return "Viewer"
        
    # 2. Check registered user database
    users_db = load_users()
    if email_clean in users_db:
        return users_db[email_clean]["role"]
        
    return None


def handle_google_oauth_callback() -> bool:
    """Process incoming OAuth code callback from Google redirect."""
    query_params = st.query_params
    code = query_params.get("code")
    
    if code:
        user_info = exchange_code_for_user_info(code)
        # Clear code from query params to avoid re-execution
        st.query_params.clear()
        
        if user_info:
            email = user_info.get("email", "")
            name = user_info.get("name") or user_info.get("given_name") or email.split("@")[0]
            picture = user_info.get("picture", "")
            
            role = map_email_to_role(email)
            if role:
                st.session_state.logged_in = True
                st.session_state.username = name
                st.session_state.email = email
                st.session_state.role = role
                st.session_state.profile_picture = picture
                st.session_state.login_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                st.toast(f"Authenticated via Google: Welcome {name} ({role})!")
                st.rerun()
                return True
            else:
                st.error(f"Your Google account ({email}) is not authorized to access Project FORESIGHT.")
                return False
    return False
