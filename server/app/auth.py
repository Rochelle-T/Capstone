"""
JWT Authentication Module

This module handles all JWT token creation, validation, and password hashing.
[JWT AUTHENTICATION]: All functions in this module are used for securing API endpoints.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
import hashlib
import os
from pydantic import BaseModel
from app.config import settings

# [JWT AUTHENTICATION]: Password hashing using hashlib (simple but adequate for MVP)
def hash_password(password: str) -> str:
    """
    [JWT AUTHENTICATION]: Hash a password for secure storage.
    Uses hashlib with salt for MVP (bcrypt preferred for production).
    """
    salt = os.urandom(32)
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
    return salt.hex() + ":" + pwd_hash.hex()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    [JWT AUTHENTICATION]: Verify a plain password against its hash.
    Used during login to validate credentials.
    """
    try:
        salt_hex, hash_hex = hashed_password.split(":")
        salt = bytes.fromhex(salt_hex)
        stored_hash = bytes.fromhex(hash_hex)
        pwd_hash = hashlib.pbkdf2_hmac('sha256', plain_password.encode(), salt, 100000)
        return pwd_hash == stored_hash
    except:
        return False

class TokenData(BaseModel):
    """[JWT AUTHENTICATION]: JWT payload structure"""
    sub: str  # subject (user_id)
    exp: datetime  # expiration time
    iat: datetime  # issued at

class Token(BaseModel):
    """[JWT AUTHENTICATION]: Response model for token endpoint"""
    access_token: str
    token_type: str
    user_id: str

class UserAuth(BaseModel):
    """[JWT AUTHENTICATION]: User credentials for login/register"""
    email: str
    password: str

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    [JWT AUTHENTICATION]: Create a JWT access token.
    Token includes user_id in 'sub' claim and expiry time.
    Token is used in Authorization header: 'Bearer {token}'
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_token(token: str) -> dict:
    """
    [JWT AUTHENTICATION]: Decode and verify a JWT token.
    Returns user_id if valid, None if expired or invalid.
    Used by get_current_user dependency in main.py to authenticate requests.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        return {"user_id": user_id}
    except jwt.InvalidTokenError:
        return None
