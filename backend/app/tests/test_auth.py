"""
Authentication API tests.

Tests for:
- POST /api/v1/auth/login - login with correct/incorrect credentials
- POST /api/v1/auth/register - user registration
- Protected endpoint access without token
"""
import pytest
from httpx import AsyncClient

from app.core.security import verify_password


@pytest.mark.asyncio
async def test_login_success(test_client: AsyncClient, test_user):
    """Test login with correct username and password returns JWT token."""
    response = await test_client.post(
        "/api/v1/auth/login",
        json={
            "username": "testuser",
            "password": "testpass123",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "expires_in" in data
    assert isinstance(data["access_token"], str)
    assert len(data["access_token"]) > 0


@pytest.mark.asyncio
async def test_login_with_email(test_client: AsyncClient, test_user):
    """Test login with email instead of username."""
    response = await test_client.post(
        "/api/v1/auth/login",
        json={
            "username": "test@example.com",
            "password": "testpass123",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data


@pytest.mark.asyncio
async def test_login_wrong_password(test_client: AsyncClient, test_user):
    """Test login with wrong password returns 401."""
    response = await test_client.post(
        "/api/v1/auth/login",
        json={
            "username": "testuser",
            "password": "wrongpassword",
        },
    )

    assert response.status_code == 401
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_login_nonexistent_user(test_client: AsyncClient):
    """Test login with non-existent user returns 401."""
    response = await test_client.post(
        "/api/v1/auth/login",
        json={
            "username": "nonexistent",
            "password": "anypassword",
        },
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_missing_fields(test_client: AsyncClient):
    """Test login with missing required fields returns 422."""
    response = await test_client.post(
        "/api/v1/auth/login",
        json={
            "username": "testuser",
            # password missing
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_success(test_client: AsyncClient):
    """Test user registration creates new user."""
    response = await test_client.post(
        "/api/v1/auth/register",
        json={
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "newpass123",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["message"] == "注册成功"
    assert "user_id" in data


@pytest.mark.asyncio
async def test_register_duplicate_username(test_client: AsyncClient, test_user):
    """Test registration with duplicate username returns 400."""
    response = await test_client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser",
            "email": "different@example.com",
            "password": "password123",
        },
    )

    assert response.status_code == 400
    data = response.json()
    assert "用户名已存在" in data["detail"]


@pytest.mark.asyncio
async def test_register_duplicate_email(test_client: AsyncClient, test_user):
    """Test registration with duplicate email returns 400."""
    response = await test_client.post(
        "/api/v1/auth/register",
        json={
            "username": "different",
            "email": "test@example.com",
            "password": "password123",
        },
    )

    assert response.status_code == 400
    data = response.json()
    assert "邮箱已被注册" in data["detail"]


@pytest.mark.asyncio
async def test_register_short_password(test_client: AsyncClient):
    """Test registration with password shorter than 6 characters returns 422."""
    response = await test_client.post(
        "/api/v1/auth/register",
        json={
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "12345",
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_protected_endpoint_without_token(test_client: AsyncClient):
    """Test accessing protected endpoint without token returns 403."""
    response = await test_client.get("/api/v1/social-tasks")

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_protected_endpoint_with_invalid_token(test_client: AsyncClient):
    """Test accessing protected endpoint with invalid token returns 401."""
    response = await test_client.get(
        "/api/v1/social-tasks",
        headers={"Authorization": "Bearer invalid_token"}
    )

    assert response.status_code == 401
