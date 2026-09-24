"""
Authentication Router
───────────────────────
Provides endpoints for operator login and session identity.
"""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.security import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    DEFAULT_USERS,
    UserOut,
    create_access_token,
    get_current_user,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


@router.post("/login", response_model=LoginResponse)
async def login(credentials: LoginRequest):
    """
    Authenticate with username and password.
    Returns a JWT access token valid for 24 hours.
    """
    user = DEFAULT_USERS.get(credentials.username.strip().lower())
    if not user or not verify_password(credentials.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username atau password tidak sesuai.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": user["username"], "role": user["role"]},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserOut(
            username=user["username"],
            role=user["role"],
            full_name=user["full_name"],
        ),
    )


@router.get("/me", response_model=UserOut)
async def get_my_profile(current_user: UserOut = Depends(get_current_user)):
    """Return currently authenticated user details."""
    return current_user
