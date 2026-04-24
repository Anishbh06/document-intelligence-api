"""
Shared test fixtures for the Document Intelligence API test suite.

All tests run against the live Docker DB via ASGI transport.
A fresh test user is registered per session; a second user is provided
to verify per-user document isolation.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app

# ── Minimal real PDF ──────────────────────────────────────────────────────────
PDF_BYTES = (
    b"%PDF-1.4\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R"
    b"/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
    b"4 0 obj<</Length 44>>stream\n"
    b"BT /F1 12 Tf 100 700 Td (NovaTech Solutions test doc.) Tj ET\n"
    b"endstream\nendobj\n"
    b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
    b"xref\n0 6\n"
    b"0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n"
    b"0000000115 00000 n \n0000000274 00000 n \n0000000368 00000 n \n"
    b"trailer<</Size 6/Root 1 0 R>>\nstartxref\n441\n%%EOF"
)

_USER_A = {"username": "testuser_a", "email": "a@test.com", "password": "passwordA1"}
_USER_B = {"username": "testuser_b", "email": "b@test.com", "password": "passwordB1"}


async def _get_token(client: AsyncClient, creds: dict) -> str:
    """Register or login a user and return its JWT."""
    r = await client.post("/api/v1/auth/register", json=creds)
    if r.status_code == 409:  # already exists — login instead
        r = await client.post("/api/v1/auth/login",
                              json={"username": creds["username"],
                                    "password": creds["password"]})
    assert r.status_code in (200, 201), f"Auth failed: {r.text}"
    return r.json()["access_token"]


# ── Session-scoped HTTP client fixtures ───────────────────────────────────────

@pytest_asyncio.fixture(scope="session")
async def client_a():
    """AsyncClient authenticated as User A."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        token = await _get_token(c, _USER_A)
        c.headers.update({"Authorization": f"Bearer {token}"})
        yield c


@pytest_asyncio.fixture(scope="session")
async def client_b():
    """AsyncClient authenticated as User B."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        token = await _get_token(c, _USER_B)
        c.headers.update({"Authorization": f"Bearer {token}"})
        yield c


@pytest_asyncio.fixture(scope="session")
async def anon_client():
    """Unauthenticated AsyncClient."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


# ── PDF file fixture ──────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def pdf_bytes():
    return PDF_BYTES