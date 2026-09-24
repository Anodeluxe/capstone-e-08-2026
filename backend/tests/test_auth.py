"""
Unit tests for Authentication & Security
────────────────────────────────────────
Tests password hashing, JWT token creation, decoding, and auth endpoints.
"""

from datetime import timedelta
import pytest
from httpx import AsyncClient, ASGITransport

from app.core.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)
from app.main import app


class TestSecurityUtilities:
    def test_password_hash_and_verify(self):
        secret = "supersecret123"
        hashed = get_password_hash(secret)
        assert hashed != secret
        assert verify_password(secret, hashed) is True
        assert verify_password("wrongpassword", hashed) is False

    def test_create_and_decode_token(self):
        data = {"sub": "admin", "role": "admin"}
        token = create_access_token(data, expires_delta=timedelta(hours=1))
        payload = decode_access_token(token)
        assert payload is not None
        assert payload.sub == "admin"
        assert payload.role == "admin"

    def test_decode_invalid_token_returns_none(self):
        payload = decode_access_token("this.is.not.a.valid.jwt.token")
        assert payload is None


@pytest.mark.asyncio
class TestAuthEndpoints:
    async def test_login_success_admin(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/login",
                json={"username": "admin", "password": "capstone2026"},
            )
            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert data["token_type"] == "bearer"
            assert data["user"]["username"] == "admin"

    async def test_login_invalid_password_fails(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/login",
                json={"username": "admin", "password": "wrongpassword"},
            )
            assert response.status_code == 401
            assert "detail" in response.json()

    async def test_get_me_with_valid_token(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            login_resp = await client.post(
                "/api/v1/auth/login",
                json={"username": "admin", "password": "capstone2026"},
            )
            token = login_resp.json()["access_token"]

            me_resp = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert me_resp.status_code == 200
            user_data = me_resp.json()
            assert user_data["username"] == "admin"
            assert user_data["role"] == "admin"
