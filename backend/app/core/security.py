"""
Security & Authentication Utilities
─────────────────────────────────────
JWT token generation, decoding, standard PBKDF2-HMAC-SHA256 password hashing,
and FastAPI user dependencies.
"""

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import os
from typing import Optional

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from app.core.config import get_settings

settings = get_settings()

bearer_scheme = HTTPBearer(auto_error=False)

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours


def get_password_hash(password: str) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 with random salt."""
    salt = os.urandom(16).hex()
    key = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), 100000
    )
    return f"pbkdf2_sha256${salt}${key.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password in constant time."""
    try:
        parts = hashed_password.split("$")
        if len(parts) != 3 or parts[0] != "pbkdf2_sha256":
            return False
        salt = bytes.fromhex(parts[1])
        expected_hex = parts[2]
        key = hashlib.pbkdf2_hmac(
            "sha256", plain_password.encode("utf-8"), salt, 100000
        )
        return hmac.compare_digest(key.hex(), expected_hex)
    except Exception:
        return False


# Default demo accounts
DEFAULT_USERS = {
    "admin": {
        "username": "admin",
        "hashed_password": get_password_hash("capstone2026"),
        "role": "admin",
        "full_name": "Toren Administrator",
    },
    "operator": {
        "username": "operator",
        "hashed_password": get_password_hash("operator123"),
        "role": "operator",
        "full_name": "Toren Operator",
    },
}


class TokenPayload(BaseModel):
    sub: str
    role: str = "operator"
    exp: Optional[int] = None


class UserOut(BaseModel):
    username: str
    role: str
    full_name: str


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": int(expire.timestamp()), "iat": int(now.timestamp())})
    return jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[TokenPayload]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        return TokenPayload(sub=username, role=payload.get("role", "operator"), exp=payload.get("exp"))
    except JWTError:
        return None


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
) -> Optional[UserOut]:
    """
    Returns the authenticated user if a valid Bearer token is provided.
    Returns None if no token or invalid token, allowing dev-mode fallback.
    """
    if not credentials or not credentials.credentials:
        return None

    token_data = decode_access_token(credentials.credentials)
    if not token_data:
        return None

    user = DEFAULT_USERS.get(token_data.sub)
    if not user:
        return UserOut(username=token_data.sub, role=token_data.role, full_name=token_data.sub.title())

    return UserOut(
        username=user["username"],
        role=user["role"],
        full_name=user["full_name"],
    )


async def get_current_user(
    user: Optional[UserOut] = Depends(get_current_user_optional),
) -> UserOut:
    """Enforces authentication. Raises 401 if unauthenticated."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
