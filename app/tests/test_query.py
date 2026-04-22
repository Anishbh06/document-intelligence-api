import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings

TEST_HEADERS = {"X-API-Key": settings.GEMINI_API_KEY}


# ---------------------------------------------------------------
# WHAT THIS FILE TESTS
# POST /api/v1/query
#
# All query tests first upload a document to get a valid document_id,
# then run queries against it. This mirrors real usage.
#
# test_query_returns_answer          — happy path: ask a question, get an answer + citations
# test_query_citations_shape         — every citation has id, chunk_index, content
# test_query_document_not_found      — query against a non-existent document_id → 404
# test_query_missing_fields          — send empty body → 422 validation error
# ---------------------------------------------------------------


@pytest.fixture
def pdf_bytes(tmp_path):
    """Single-page PDF with enough text to answer a question about NovaTech."""
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
    p = tmp_path / "novatech.pdf"
    p.write_bytes(content)
    return p


async def upload_pdf(client, pdf_bytes) -> int:
    """Helper: upload a PDF and return the document_id."""
    with open(pdf_bytes, "rb") as f:
        response = await client.post(
            "/api/v1/upload",
            files={"file": ("novatech.pdf", f, "application/pdf")},
            headers=TEST_HEADERS,
        )
    assert response.status_code == 200, f"Upload failed: {response.text}"
    return response.json()["job"]["id"]


async def wait_for_document_id(client, job_id: int, retries: int = 30) -> int:
    for _ in range(retries):
        response = await client.get(f"/api/v1/jobs/{job_id}", headers=TEST_HEADERS)
        assert response.status_code == 200, f"Job lookup failed: {response.text}"
        payload = response.json()
        if payload["status"] == "completed" and payload["document_id"]:
            return payload["document_id"]
        if payload["status"] == "failed":
            raise AssertionError(f"Job failed: {payload.get('error_message')}")
    raise AssertionError("Timed out waiting for document processing")


@pytest.mark.asyncio
async def test_query_returns_answer(pdf_bytes):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        job_id = await upload_pdf(client, pdf_bytes)
        doc_id = await wait_for_document_id(client, job_id)

        response = await client.post(
            "/api/v1/query",
            json={"document_id": doc_id, "question": "What is this document about?"},
            headers=TEST_HEADERS,
        )

    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert isinstance(data["answer"], str)
    assert len(data["answer"]) > 0
    assert "citations" in data
    assert isinstance(data["citations"], list)
    assert len(data["citations"]) >= 1


@pytest.mark.asyncio
async def test_query_citations_shape(pdf_bytes):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        job_id = await upload_pdf(client, pdf_bytes)
        doc_id = await wait_for_document_id(client, job_id)

        response = await client.post(
            "/api/v1/query",
            json={"document_id": doc_id, "question": "Summarise this document."},
            headers=TEST_HEADERS,
        )

    assert response.status_code == 200
    for citation in response.json()["citations"]:
        assert "id" in citation
        assert "chunk_index" in citation
        assert "content" in citation
        assert isinstance(citation["id"], int)
        assert isinstance(citation["chunk_index"], int)
        assert isinstance(citation["content"], str)


@pytest.mark.asyncio
async def test_query_document_not_found():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/query",
            json={"document_id": 999999, "question": "Does this exist?"},
            headers=TEST_HEADERS,
        )

    assert response.status_code == 404
    assert "not found" in response.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_query_missing_fields():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/v1/query", json={}, headers=TEST_HEADERS)

    assert response.status_code == 422  # FastAPI validation error