"""Authentication wrapper logic for Project FORESIGHT."""
from __future__ import annotations

from auth.users import verify_credentials, User

def authenticate_user(email: str, password: str) -> User | None:
    """Validate user credentials and return the user profile if valid."""
    if not email or not password:
        return None
    return verify_credentials(email, password)
