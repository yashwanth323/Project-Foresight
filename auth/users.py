"""User management compatibility bridge for Project FORESIGHT."""
from __future__ import annotations

from typing import TypedDict, Any
from auth.auth_utils import hash_password, validate_email_format
from auth.database import (
    authenticate_user as db_authenticate_user,
    create_user as db_create_user,
    get_user_by_email,
    get_db_connection,
)

class User(TypedDict):
    email: str
    password: str
    username: str
    role: str

def load_users() -> dict[str, User]:
    """Return all active users from SQLite database formatted as a dictionary keyed by email."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE is_active = 1;")
        rows = cursor.fetchall()
        result: dict[str, User] = {}
        for r in rows:
            u_dict = dict(r)
            result[u_dict["email"].lower()] = {
                "email": u_dict["email"],
                "password": u_dict["password_hash"],
                "username": u_dict["username"],
                "role": u_dict["role"],
            }
        return result
    finally:
        conn.close()

def verify_credentials(email_or_username: str, password_raw: str) -> User | None:
    """Verify credentials against SQLite database."""
    res = db_authenticate_user(email_or_username, password_raw)
    if res:
        return {
            "email": res["email"],
            "password": res["password"],
            "username": res["username"],
            "role": res["role"],
        }
    return None

def register_new_user(username: str, email: str, password_raw: str, role: str) -> tuple[bool, str]:
    """Register a new user via auth.database.create_user."""
    full_name = username  # Fallback full name for backward compatibility
    return db_create_user(full_name, username, email, password_raw, role)
