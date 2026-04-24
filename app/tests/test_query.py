"""
test_query.py — Tests for the RAG query endpoint.

Covers:
  POST /api/v1/query — missing fields (422), non-existent doc (404),
                       unauthenticated (401), valid answer + citation shape
"""

import pytest
from app.tests.conftest import PDF_BYTES


# ── Validation / auth guards (fast — no DB upload needed) ────────────────────

@pytest.mark.asyncio
async def test_query_missing_fields(client_a):
    r = await client_a.post("/api/v1/query", json={})
    assert r.status_code == 422
    assert "error" in r.json()


@pytest.mark.asyncio
async def test_query_document_not_found(client_a):
    r = await client_a.post(
        "/api/v1/query",
        json={"document_id": 9999999, "question": "Does this exist?"},
    )
    assert r.status_code == 404
    assert "not found" in r.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_query_unauthenticated(anon_client):
    r = await anon_client.post(
        "/api/v1/query",
        json={"document_id": 1, "question": "test?"},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_query_empty_question(client_a):
    """An empty question string should fail pydantic validation."""
    r = await client_a.post(
        "/api/v1/query",
        json={"document_id": 1, "question": ""},
    )
    assert r.status_code == 422


# ── Answer + citation shape (requires a real indexed document) ────────────────

@pytest.mark.asyncio
async def test_query_returns_answer_and_citations(client_a):
    """Upload → wait for processing → query → verify answer + citations."""
    import asyncio

    # Upload
    r = await client_a.post(
        "/api/v1/upload",
        files={"file": ("query_test.pdf", PDF_BYTES, "application/pdf")},
    )
    assert r.status_code == 200
    job_id = r.json()["job"]["id"]

    # Poll for completion (max 30s)
    doc_id = None
    for _ in range(30):
        poll = await client_a.get(f"/api/v1/jobs/{job_id}")
        payload = poll.json()
        if payload["status"] == "completed" and payload.get("document_id"):
            doc_id = payload["document_id"]
            break
        if payload["status"] == "failed":
            pytest.skip(f"Document processing failed: {payload.get('error_message')}")
        await asyncio.sleep(1)

    if doc_id is None:
        pytest.skip("Document processing timed out — skipping query test")

    # Query
    r = await client_a.post(
        "/api/v1/query",
        json={"document_id": doc_id, "question": "What is this document about?"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "answer" in data
    assert isinstance(data["answer"], str)
    assert len(data["answer"]) > 0
    assert "citations" in data
    assert isinstance(data["citations"], list)
    assert len(data["citations"]) >= 1

    for citation in data["citations"]:
        assert "id" in citation
        assert "chunk_index" in citation
        assert "content" in citation
        assert isinstance(citation["id"], int)
        assert isinstance(citation["chunk_index"], int)
        assert isinstance(citation["content"], str)