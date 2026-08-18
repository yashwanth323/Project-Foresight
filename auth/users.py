"""User management, secure password hashing, and persistent storage for Project FORESIGHT."""
from __future__ import annotations

import json
import re
import hashlib
from pathlib import Path
from typing import TypedDict

class User(TypedDict):
    email: str
    password: str  # Hashed SHA-256 password
    username: str
    role: str

USERS_JSON_PATH = Path(__file__).resolve().parent / "users.json"

def hash_password(password: str) -> str:
    """Generate SHA-256 hash for secure password storage."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def get_default_users() -> dict[str, User]:
    """Return default accounts with pre-hashed passwords."""
    return {
        "admin@foresight.ai": {
            "email": "admin@foresight.ai",
            "password": hash_password("admin123"),
            "username": "Administrator",
            "role": "Administrator",
        },
        "planner@foresight.ai": {
            "email": "planner@foresight.ai",
            "password": hash_password("planner123"),
            "username": "Planner",
            "role": "Inventory Planner",
        },
        "viewer@foresight.ai": {
            "email": "viewer@foresight.ai",
            "password": hash_password("viewer123"),
            "username": "Viewer",
            "role": "Viewer",
        }
    }

def load_users() -> dict[str, User]:
    """Load users database from users.json, fallback to defaults if missing."""
    if not USERS_JSON_PATH.exists():
        users = get_default_users()
        save_users(users)
        return users
        
    try:
        with open(USERS_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return get_default_users()

def save_users(users: dict[str, User]) -> None:
    """Write users database to users.json securely."""
    try:
        USERS_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(USERS_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=4)
    except Exception:
        pass

# Global in-memory cache of users (populated on import/load)
USERS = load_users()

def verify_credentials(email_or_username: str, password_raw: str) -> User | None:
    """Verify raw password against stored hashed passwords (matching email or username)."""
    users_db = load_users()
    search_key = email_or_username.strip().lower()
    
    # 1. Search by email key
    user = users_db.get(search_key)
    
    # 2. Search by username if email match is not found
    if not user:
        for u in users_db.values():
            if u["username"].strip().lower() == search_key:
                user = u
                break
                
    if user:
        hashed = hash_password(password_raw)
        if user["password"] == hashed:
            return user
            
    return None

def validate_email_format(email: str) -> bool:
    """Check standard email address regex validation."""
    regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(regex, email.strip()))

def register_new_user(username: str, email: str, password_raw: str, role: str) -> tuple[bool, str]:
    """Validate and register a new user in the persistent JSON store.
    
    Role Security: Public registrations default to Planner; Administrators cannot be created publicly.
    """
    users_db = load_users()
    
    email_clean = email.strip().lower()
    username_clean = username.strip()
    username_lower = username_clean.lower()
    
    # 1. Required fields
    if not username_clean or not email_clean or not password_raw:
        return False, "All required fields must be completed."
        
    # 2. Email format validation
    if not validate_email_format(email):
        return False, "Invalid email address format."
        
    # 3. Minimum password length
    if len(password_raw) < 6:
        return False, "Password must be at least 6 characters long."
        
    # 4. Role Security - restrict admin creation
    if role == "Administrator":
        return False, "Administrator account creation is restricted."
        
    # 5. Prevent duplicate usernames
    for u in users_db.values():
        if u["username"].strip().lower() == username_lower:
            return False, "Username is already taken."
            
    # 6. Prevent duplicate email addresses
    if email_clean in users_db:
        return False, "Email address is already registered."
        
    # 7. Hash password and save new record
    new_user: User = {
        "email": email_clean,
        "password": hash_password(password_raw),
        "username": username_clean,
        "role": role
    }
    
    users_db[email_clean] = new_user
    save_users(users_db)
    
    return True, "Account created successfully. Please sign in."
