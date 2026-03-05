import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestRegistration:
    async def test_register_success(self, client: AsyncClient):
        unique_id = uuid.uuid4().hex[:8]
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"newuser_{unique_id}@example.com",
                "password": "securepass123",
                "full_name": "New User",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert "email" in data
        assert data["full_name"] == "New User"
        assert data["is_active"] is True
        assert "id" in data

    async def test_register_duplicate_email(self, client: AsyncClient, registered_user: dict):
        # Try to register with same email
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": registered_user["_email"],
                "password": "anotherpass123",
                "full_name": "Another User",
            },
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Email already registered"

    async def test_register_invalid_email(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "invalid-email",
                "password": "password123",
                "full_name": "Test User",
            },
        )

        assert response.status_code == 422

    async def test_register_short_password(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "valid@example.com",
                "password": "short",
                "full_name": "Test User",
            },
        )

        assert response.status_code == 422


@pytest.mark.asyncio
class TestLogin:
    async def test_login_success(self, client: AsyncClient, registered_user: dict):
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": registered_user["_email"],
                "password": registered_user["_password"],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(self, client: AsyncClient, registered_user: dict):
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": registered_user["_email"],
                "password": "wrongpassword",
            },
        )

        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid credentials"

    async def test_login_nonexistent_user(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "password123",
            },
        )

        assert response.status_code == 401


@pytest.mark.asyncio
class TestTokenValidation:
    async def test_valid_token_access(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/v1/organization",
            json={"org_name": "Test Org"},
            headers=auth_headers,
        )

        assert response.status_code == 201

    async def test_no_token_rejected(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/organization",
            json={"org_name": "Test Org"},
        )

        # 401 Unauthorized when no credentials provided
        assert response.status_code == 401

    async def test_invalid_token_rejected(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/organization",
            json={"org_name": "Test Org"},
            headers={"Authorization": "Bearer invalid_token"},
        )

        assert response.status_code == 401
