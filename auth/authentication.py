"""Authentication wrapper module for Project FORESIGHT."""
from __future__ import annotations

from typing import Any
from auth.database import authenticate_user as db_authenticate_user

def authenticate_user(email_or_username: str, password_raw: str) -> dict[str, Any] | None:
    """Validate user credentials against SQLite database and return user record if valid."""
    return db_authenticate_user(email_or_username, password_raw)
