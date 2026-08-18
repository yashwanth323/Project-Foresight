"""Google OAuth 2.0 authentication service for Project FORESIGHT."""
from __future__ import annotations

import os
import json
import logging
import urllib.parse
import urllib.request
import streamlit as st

# Setup logger
logger = logging.getLogger("FORESIGHT.OAuth")

# Automatically load .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv(override=False)
except Exception:
    pass

# Environment variable keys
ENV_CLIENT_ID = "GOOGLE_CLIENT_ID"
ENV_CLIENT_SECRET = "GOOGLE_CLIENT_SECRET"
ENV_REDIRECT_URI = "GOOGLE_REDIRECT_URI"

# Google OAuth Endpoints
GOOGLE_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_ENDPOINT = "https://www.googleapis.com/oauth2/v3/userinfo"


def get_secret(key: str) -> str | None:
    """Retrieve secret key from os.environ first, then .env, then .streamlit/secrets.toml safely.
    
    Priority order:
    1. Environment Variables / .env
    2. .streamlit/secrets.toml
    """
    # Force re-check load_dotenv in case .env was modified at runtime
    try:
        from dotenv import load_dotenv
        load_dotenv(override=False)
    except Exception:
        pass

    # 1. Check os.environ first (populated by OS env or python-dotenv)
    val = os.environ.get(key)
    if val:
        return val.strip()
        
    # 2. Check st.secrets safely catching StreamlitSecretNotFoundError and other exceptions
    try:
        if hasattr(st, "secrets") and st.secrets is not None:
            # Check direct top-level key
            if key in st.secrets:
                sec_val = st.secrets[key]
                if sec_val:
                    return str(sec_val).strip()
                    
            # Check under "google" or "GOOGLE" or "oauth" section headers
            for sec_name in ["google", "GOOGLE", "oauth", "OAUTH"]:
                if sec_name in st.secrets:
                    sec_obj = st.secrets[sec_name]
                    if isinstance(sec_obj, dict) or hasattr(sec_obj, "get"):
                        if key in sec_obj:
                            val = sec_obj.get(key)
                            if val:
                                return str(val).strip()
                        # Also check without GOOGLE_ prefix (e.g. CLIENT_ID or client_id)
                        short_k = key.replace("GOOGLE_", "")
                        for candidate_k in [short_k, short_k.lower()]:
                            if candidate_k in sec_obj:
                                val = sec_obj.get(candidate_k)
                                if val:
                                    return str(val).strip()
    except Exception:
        # Silently catch StreamlitSecretNotFoundError, FileNotFoundError, KeyError, AttributeError, etc.
        pass
        
    return None


def get_oauth_credentials() -> tuple[str | None, str | None, str | None]:
    """Retrieve Google OAuth credentials safely without throwing StreamlitSecretNotFoundError.
    
    Returns (client_id, client_secret, redirect_uri) if ALL exist, otherwise (None, None, None).
    """
    client_id = get_secret(ENV_CLIENT_ID)
    client_secret = get_secret(ENV_CLIENT_SECRET)
    redirect_uri = get_secret(ENV_REDIRECT_URI)
    
    if client_id and client_secret and redirect_uri:
        return client_id, client_secret, redirect_uri
        
    return None, None, None


def is_google_oauth_configured() -> bool:
    """Check if Google OAuth credentials are completely defined and log diagnostic status."""
    cid = get_secret(ENV_CLIENT_ID)
    secret = get_secret(ENV_CLIENT_SECRET)
    uri = get_secret(ENV_REDIRECT_URI)
    
    cid_loaded = "Yes" if cid else "No"
    secret_loaded = "Yes" if secret else "No"
    uri_loaded = "Yes" if uri else "No"
    
    # Print diagnostic logs to console without revealing secret values
    diag_msg = (
        f"Google OAuth Diagnostics:\n"
        f"  Google Client ID loaded: {cid_loaded}\n"
        f"  Google Client Secret loaded: {secret_loaded}\n"
        f"  Google Redirect URI loaded: {uri_loaded}"
    )
    print(diag_msg)
    logger.info(diag_msg)
    
    configured = bool(cid and secret and uri)
    if not configured:
        console_warn = (
            "[OAuth Notice]: Google OAuth is not fully configured (missing Client ID, Secret, or Redirect URI). "
            "Hiding Google Sign-In button and using local authentication."
        )
        print(console_warn)
        logger.warning(console_warn)
        
    return configured


def get_google_auth_url() -> str | None:
    """Construct Google OAuth 2.0 login URL."""
    client_id, _, redirect_uri = get_oauth_credentials()
    if not client_id or not redirect_uri:
        return None
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent"
    }
    return f"{GOOGLE_AUTH_ENDPOINT}?{urllib.parse.urlencode(params)}"


def exchange_code_for_user_info(code: str) -> dict | None:
    """Exchange authorization code for Google user profile info."""
    client_id, client_secret, redirect_uri = get_oauth_credentials()
    if not client_id or not client_secret or not redirect_uri:
        logger.warning("Attempted OAuth exchange without valid credentials.")
        return None
        
    # 1. Exchange code for access token
    token_data = urllib.parse.urlencode({
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code"
    }).encode("utf-8")
    
    req_token = urllib.request.Request(
        GOOGLE_TOKEN_ENDPOINT, 
        data=token_data, 
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    try:
        with urllib.request.urlopen(req_token) as resp:
            token_json = json.loads(resp.read().decode("utf-8"))
            access_token = token_json.get("access_token")
    except Exception as exc:
        st.error(f"Google Token Exchange Failed: {exc}")
        return None
        
    if not access_token:
        return None
        
    # 2. Fetch user profile with access token
    req_user = urllib.request.Request(
        GOOGLE_USERINFO_ENDPOINT,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    try:
        with urllib.request.urlopen(req_user) as resp:
            user_info = json.loads(resp.read().decode("utf-8"))
            return user_info
    except Exception as exc:
        st.error(f"Google User Info Fetch Failed: {exc}")
        return None
