"""
test_auth.py — Tests for JWT authentication endpoints.

Covers:
  POST /api/v1/auth/register  — happy path, duplicate, weak password, short username
  POST /api/v1/auth/login     — happy path, wrong password, unknown user
  GET  /api/v1/auth/me        — with valid token, with no token
"""

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.mark.asyncio
async def test_register_success():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/v1/auth/register", json={
            "username": "reg_test_ok",
            "email": "reg_ok@test.com",
            "password": "validpass99",
        })
    # 201 on first run; 409 if test DB already has this user from a previous run
    assert r.status_code in (201, 409)
    if r.status_code == 201:
        body = r.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"
        assert body["user"]["username"] == "reg_test_ok"
        assert body["user"]["email"] == "reg_ok@test.com"
        assert "hashed_password" not in body["user"]


@pytest.mark.asyncio
async def test_register_duplicate():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        payload = {"username": "dup_user", "email": "dup@test.com", "password": "validpass99"}
        await c.post("/api/v1/auth/register", json=payload)
        r = await c.post("/api/v1/auth/register", json=payload)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "username_taken"


@pytest.mark.asyncio
async def test_register_weak_password():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/v1/auth/register", json={
            "username": "weakpwduser",
            "email": "weak@test.com",
            "password": "short",
        })
    assert r.status_code == 422
    body = r.json()
    assert "error" in body
    assert "8" in body["error"]["message"] or "password" in body["error"]["message"].lower()


@pytest.mark.asyncio
async def test_register_short_username():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/v1/auth/register", json={
            "username": "ab",
            "email": "short@test.com",
            "password": "validpass99",
        })
    assert r.status_code == 422
    assert "error" in r.json()


@pytest.mark.asyncio
async def test_login_success():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post("/api/v1/auth/register", json={
            "username": "login_ok_user",
            "email": "login_ok@test.com",
            "password": "validpass99",
        })
        r = await c.post("/api/v1/auth/login", json={
            "username": "login_ok_user",
            "password": "validpass99",
        })
    assert r.status_code == 200
    assert "access_token" in r.json()


@pytest.mark.asyncio
async def test_login_wrong_password():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post("/api/v1/auth/register", json={
            "username": "wrongpwd_user",
            "email": "wrongpwd@test.com",
            "password": "validpass99",
        })
        r = await c.post("/api/v1/auth/login", json={
            "username": "wrongpwd_user",
            "password": "notmypassword",
        })
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "invalid_credentials"


@pytest.mark.asyncio
async def test_login_unknown_user():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/v1/auth/login", json={
            "username": "ghost_user_xyz",
            "password": "doesnotmatter1",
        })
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_me_authenticated(client_a):
    r = await client_a.get("/api/v1/auth/me")
    assert r.status_code == 200
    body = r.json()
    assert body["username"] == "testuser_a"
    assert "hashed_password" not in body
    assert body["is_active"] is True


@pytest.mark.asyncio
async def test_me_unauthenticated(anon_client):
    r = await anon_client.get("/api/v1/auth/me")
    assert r.status_code == 401
    assert r.json()["error"]["code"] in ("unauthorized", "not_authenticated")
