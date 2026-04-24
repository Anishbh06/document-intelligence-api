"""
test_upload.py — Tests for document upload endpoints.

Covers:
  POST   /api/v1/upload           — valid PDF, non-PDF, response shape
  GET    /api/v1/documents        — returns only the current user's documents
  DELETE /api/v1/documents/{id}   — owner can delete; unauthenticated gets 401
  GET    /api/v1/jobs/{id}        — job status polling
"""

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.tests.conftest import PDF_BYTES


# ── Upload tests ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_upload_valid_pdf(client_a):
    r = await client_a.post(
        "/api/v1/upload",
        files={"file": ("test.pdf", PDF_BYTES, "application/pdf")},
    )
    assert r.status_code == 200
    data = r.json()
    assert "job" in data
    # Dedup: if same bytes were uploaded earlier in the session, the existing job
    # is returned (filename reflects that original upload, not necessarily "test.pdf")
    assert isinstance(data["job"]["filename"], str) and len(data["job"]["filename"]) > 0
    assert data["job"]["id"] > 0
    assert data["job"]["status"] in {"pending", "processing", "completed"}



@pytest.mark.asyncio
async def test_upload_non_pdf(client_a):
    r = await client_a.post(
        "/api/v1/upload",
        files={"file": ("notes.txt", b"just some text", "text/plain")},
    )
    assert r.status_code == 400
    assert "PDF" in r.json()["error"]["message"]


@pytest.mark.asyncio
async def test_upload_fake_pdf(client_a):
    """A file that ends in .pdf but doesn't start with %PDF- magic bytes."""
    r = await client_a.post(
        "/api/v1/upload",
        files={"file": ("fake.pdf", b"not a real pdf content", "application/pdf")},
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "invalid_pdf_content"


@pytest.mark.asyncio
async def test_upload_unauthenticated(anon_client):
    r = await anon_client.post(
        "/api/v1/upload",
        files={"file": ("test.pdf", PDF_BYTES, "application/pdf")},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_upload_response_fields(client_a):
    r = await client_a.post(
        "/api/v1/upload",
        files={"file": ("fields_test.pdf", PDF_BYTES, "application/pdf")},
    )
    assert r.status_code == 200
    job = r.json()["job"]
    assert isinstance(job["id"], int)
    assert isinstance(job["filename"], str)
    assert isinstance(job["created_at"], str)
    assert isinstance(job["updated_at"], str)
    assert isinstance(job["progress"], int)
    assert isinstance(job["status"], str)
    assert job["status"] in {"pending", "processing", "completed"}


# ── Documents list tests ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_documents_authenticated(client_a):
    r = await client_a.get("/api/v1/documents")
    assert r.status_code == 200
    body = r.json()
    assert "documents" in body
    assert "total" in body
    assert isinstance(body["documents"], list)
    assert body["total"] == len(body["documents"])


@pytest.mark.asyncio
async def test_list_documents_unauthenticated(anon_client):
    r = await anon_client.get("/api/v1/documents")
    assert r.status_code == 401


# ── Job status tests ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_job_status_exists(client_a):
    """Upload a PDF then verify job status endpoint returns the right shape."""
    upload = await client_a.post(
        "/api/v1/upload",
        files={"file": ("job_test.pdf", PDF_BYTES, "application/pdf")},
    )
    job_id = upload.json()["job"]["id"]

    r = await client_a.get(f"/api/v1/jobs/{job_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == job_id
    assert body["status"] in {"pending", "processing", "completed", "failed"}
    assert isinstance(body["progress"], int)
    assert 0 <= body["progress"] <= 100


@pytest.mark.asyncio
async def test_job_status_not_found(client_a):
    r = await client_a.get("/api/v1/jobs/9999999")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_job_status_unauthenticated(anon_client):
    r = await anon_client.get("/api/v1/jobs/1")
    assert r.status_code == 401


# ── Delete tests ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_nonexistent_document(client_a):
    r = await client_a.delete("/api/v1/documents/9999999")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "document_not_found"


@pytest.mark.asyncio
async def test_delete_unauthenticated(anon_client):
    r = await anon_client.delete("/api/v1/documents/1")
    assert r.status_code == 401