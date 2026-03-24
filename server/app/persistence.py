"""
User Persistence Manager

Implements file-based user storage for MVP development.
In production, replace with PostgreSQL or other database.

[JWT AUTHENTICATION]: Stores hashed passwords and user metadata persistently
"""

import json
import os
from pathlib import Path
from typing import Dict, Optional

# Store users in a JSON file instead of memory
USERS_FILE = Path(__file__).parent.parent / "users.json"

def _load_users_db() -> Dict:
    """Load users from persistent storage"""
    if USERS_FILE.exists():
        try:
            with open(USERS_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def _save_users_db(users: Dict) -> None:
    """Save users to persistent storage"""
    try:
        with open(USERS_FILE, 'w') as f:
            json.dump(users, f, indent=2)
        print(f"[AUTH] Users saved to {USERS_FILE}")
    except Exception as e:
        print(f"[AUTH] Error saving users: {e}")

# [JWT AUTHENTICATION]: Load users on startup
users_db = _load_users_db()
print(f"[AUTH] Loaded {len(users_db)} users from persistent storage")

def add_user(user_id: str, email: str, password_hash: str, username: str) -> None:
    """[JWT AUTHENTICATION]: Add user to persistent storage"""
    users_db[user_id] = {
        "email": email,
        "password_hash": password_hash,
        "username": username
    }
    _save_users_db(users_db)

def get_user(user_id: str) -> Optional[Dict]:
    """[JWT AUTHENTICATION]: Get user from persistent storage"""
    return users_db.get(user_id)

def user_exists(email: str) -> bool:
    """Check if user with email already exists"""
    for user in users_db.values():
        if user["email"] == email:
            return True
    return False

def get_users_db() -> Dict:
    """Get entire users database"""
    return users_db
