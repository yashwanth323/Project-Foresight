"""SQLite database management, user seeding, and authentication queries for Project FORESIGHT."""
from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import TypedDict, Any

from auth.auth_utils import (
    hash_password,
    verify_password,
    validate_email_format,
    validate_password_strength,
)

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "foresight.db"

class UserRecord(TypedDict):
    id: int
    full_name: str
    username: str
    email: str
    password_hash: str
    role: str
    created_at: str
    is_active: int

def get_db_connection() -> sqlite3.Connection:
    """Create and return a thread-safe connection to foresight.db."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_database() -> None:
    """Initialize the SQLite database schema and seed default users if empty."""
    conn = get_db_connection()
    try:
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    full_name TEXT NOT NULL,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1
                );
            """)
        create_default_users(conn)
    finally:
        conn.close()

def create_default_users(conn: sqlite3.Connection | None = None) -> None:
    """Seed default system accounts if the users table is empty."""
    close_after = False
    if conn is None:
        conn = get_db_connection()
        close_after = True
        
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM users;")
        row = cursor.fetchone()
        count = row["cnt"] if row else 0
        
        if count == 0:
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            default_accounts = [
                (
                    "System Administrator",
                    "admin",
                    "admin@foresight.ai",
                    hash_password("admin123"),
                    "Administrator",
                    now_str,
                    1
                ),
                (
                    "Inventory Planner",
                    "planner",
                    "planner@foresight.ai",
                    hash_password("planner123"),
                    "Inventory Planner",
                    now_str,
                    1
                ),
                (
                    "Executive Viewer",
                    "viewer",
                    "viewer@foresight.ai",
                    hash_password("viewer123"),
                    "Viewer",
                    now_str,
                    1
                ),
            ]
            cursor.executemany("""
                INSERT INTO users (full_name, username, email, password_hash, role, created_at, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?);
            """, default_accounts)
            conn.commit()
    finally:
        if close_after and conn:
            conn.close()

def email_exists(email: str) -> bool:
    """Check if an email address already exists in the database."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM users WHERE LOWER(email) = LOWER(?);", (email.strip(),))
        return cursor.fetchone() is not None
    finally:
        conn.close()

def username_exists(username: str) -> bool:
    """Check if a username already exists in the database."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM users WHERE LOWER(username) = LOWER(?);", (username.strip(),))
        return cursor.fetchone() is not None
    finally:
        conn.close()

def load_users() -> dict[str, dict[str, Any]]:
    """Return all active users from SQLite database formatted as a dictionary keyed by email."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE is_active = 1;")
        rows = cursor.fetchall()
        result: dict[str, dict[str, Any]] = {}
        for r in rows:
            u_dict = dict(r)
            result[u_dict["email"].lower()] = {
                "email": u_dict["email"],
                "password": u_dict["password_hash"],
                "username": u_dict["username"],
                "role": u_dict["role"],
                "full_name": u_dict["full_name"],
            }
        return result
    finally:
        conn.close()

def get_user_by_email(email: str) -> dict[str, Any] | None:
    """Retrieve an active user record by email address."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE LOWER(email) = LOWER(?) AND is_active = 1;", (email.strip(),))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def get_user_by_username(username: str) -> dict[str, Any] | None:
    """Retrieve an active user record by username."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE LOWER(username) = LOWER(?) AND is_active = 1;", (username.strip(),))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def authenticate_user(email_or_username: str, password_raw: str) -> dict[str, Any] | None:
    """Authenticate a user using either email or username and verify bcrypt password hash."""
    if not email_or_username or not password_raw:
        return None
        
    query_val = email_or_username.strip()
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM users 
            WHERE (LOWER(email) = LOWER(?) OR LOWER(username) = LOWER(?)) 
            AND is_active = 1;
        """, (query_val, query_val))
        row = cursor.fetchone()
        if not row:
            return None
            
        user = dict(row)
        if verify_password(password_raw, user["password_hash"]):
            return {
                "id": user["id"],
                "full_name": user["full_name"],
                "username": user["username"],
                "email": user["email"],
                "role": user["role"],
                "password": user["password_hash"],  # For backward compatibility
            }
        return None
    finally:
        conn.close()

def create_user(full_name: str, username: str, email: str, password_raw: str, role: str) -> tuple[bool, str]:
    """Validate inputs and register a new user in SQLite database.
    
    Role Security: Administrator accounts cannot be self-registered.
    """
    fn_clean = full_name.strip()
    un_clean = username.strip()
    em_clean = email.strip().lower()
    
    # 1. Full name required
    if not fn_clean:
        return False, "Full name is required."
        
    # 2. Username required
    if not un_clean:
        return False, "Username is required."
        
    # 3. Email required & format validation
    if not em_clean or not validate_email_format(em_clean):
        return False, "Please enter a valid email address."
        
    # 4. Role Security - restrict Administrator creation
    if role == "Administrator":
        return False, "Administrator account creation is restricted."
        
    # 5. Check allowed roles
    if role not in ["Inventory Planner", "Viewer"]:
        return False, "Invalid role selected."
        
    # 6. Check unique username
    if username_exists(un_clean):
        return False, "Username is already taken. Please choose another."
        
    # 7. Check unique email
    if email_exists(em_clean):
        return False, "Email address is already registered. Please sign in or use another email."
        
    # 8. Password strength validation
    valid_pass, pass_err = validate_password_strength(password_raw)
    if not valid_pass:
        return False, pass_err
        
    # 9. Hash password and insert record
    pass_hash = hash_password(password_raw)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    conn = get_db_connection()
    try:
        with conn:
            conn.execute("""
                INSERT INTO users (full_name, username, email, password_hash, role, created_at, is_active)
                VALUES (?, ?, ?, ?, ?, ?, 1);
            """, (fn_clean, un_clean, em_clean, pass_hash, role, now_str))
        return True, "Account created successfully. Please sign in."
    except sqlite3.IntegrityError:
        return False, "Username or email already exists."
    except Exception as exc:
        return False, f"Failed to create account: {exc}"
    finally:
        conn.close()

def update_password(email: str, new_password_raw: str) -> tuple[bool, str]:
    """Validate password strength, hash using bcrypt, and update password for matching email."""
    em_clean = email.strip().lower()
    
    # 1. Verify user exists
    user = get_user_by_email(em_clean)
    if not user:
        return False, "No account found matching this email address."
        
    # 2. Validate password strength
    valid_pass, pass_err = validate_password_strength(new_password_raw)
    if not valid_pass:
        return False, pass_err
        
    # 3. Hash new password and update record
    pass_hash = hash_password(new_password_raw)
    
    conn = get_db_connection()
    try:
        with conn:
            conn.execute("""
                UPDATE users SET password_hash = ? WHERE LOWER(email) = LOWER(?);
            """, (pass_hash, em_clean))
        return True, "Password reset successfully. You can now sign in with your new password."
    except Exception as exc:
        return False, f"Failed to update password: {exc}"
    finally:
        conn.close()
