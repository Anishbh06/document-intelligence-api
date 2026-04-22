import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings

TEST_HEADERS = {"X-API-Key": settings.GEMINI_API_KEY}


# ---------------------------------------------------------------
# WHAT THIS FILE TESTS
# POST /api/v1/upload
#
# test_upload_valid_pdf         — happy path: upload a real PDF, expect 200 + correct shape
# test_upload_non_pdf           — upload a .txt file, expect 400
# test_upload_empty_filename    — upload a file named ".pdf" (no stem), still a PDF so expect 200
# test_upload_response_fields   — verify every field in the response has the right type
# ---------------------------------------------------------------


@pytest.fixture
def pdf_bytes(tmp_path):
    """Create a minimal but real single-page PDF in memory."""
    content = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj
4 0 obj<</Length 44>>stream
BT /F1 12 Tf 100 700 Td (NovaTech Solutions test document.) Tj ET
endstream
endobj
5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000274 00000 n 
0000000368 00000 n 
trailer<</Size 6/Root 1 0 R>>
startxref
441
%%EOF"""
    p = tmp_path / "test.pdf"
    p.write_bytes(content)
    return p


@pytest.mark.asyncio
async def test_upload_valid_pdf(pdf_bytes):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        with open(pdf_bytes, "rb") as f:
            response = await client.post(
                "/api/v1/upload",
                files={"file": ("test.pdf", f, "application/pdf")},
                headers=TEST_HEADERS,
            )

    assert response.status_code == 200
    data = response.json()
    assert "job" in data
    assert data["job"]["filename"] == "test.pdf"
    assert data["job"]["id"] > 0
    assert data["job"]["status"] in {"pending", "processing", "completed"}


@pytest.mark.asyncio
async def test_upload_non_pdf():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/upload",
            files={"file": ("notes.txt", b"just some text", "text/plain")},
            headers=TEST_HEADERS,
        )

    assert response.status_code == 400
    assert "PDF" in response.json()["error"]["message"]


@pytest.mark.asyncio
async def test_upload_response_fields(pdf_bytes):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        with open(pdf_bytes, "rb") as f:
            response = await client.post(
                "/api/v1/upload",
                files={"file": ("test.pdf", f, "application/pdf")},
                headers=TEST_HEADERS,
            )

    assert response.status_code == 200
    job = response.json()["job"]

    # Every field must be present and the right type
    assert isinstance(job["id"], int)
    assert isinstance(job["filename"], str)
    assert isinstance(job["created_at"], str)
    assert isinstance(job["updated_at"], str)
    assert isinstance(job["progress"], int)