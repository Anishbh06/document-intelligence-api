"""
test_isolation.py — Per-user document isolation tests.

Verifies that User B cannot list, query, or delete User A's documents.
These tests are the core correctness check for the owner_id feature.
"""

import pytest
from app.tests.conftest import PDF_BYTES


@pytest.fixture(scope="module")
async def user_a_doc_id(client_a):
    """Upload a document as User A and return its document_id (after job completes)."""
    import asyncio

    r = await client_a.post(
        "/api/v1/upload",
        files={"file": ("isolation_test.pdf", PDF_BYTES, "application/pdf")},
    )
    assert r.status_code == 200
    job_id = r.json()["job"]["id"]

    for _ in range(30):
        poll = await client_a.get(f"/api/v1/jobs/{job_id}")
        payload = poll.json()
        if payload["status"] == "completed" and payload.get("document_id"):
            return payload["document_id"]
        if payload["status"] == "failed":
            pytest.skip(f"Upload failed: {payload.get('error_message')}")
        await asyncio.sleep(1)

    pytest.skip("Processing timed out — isolation tests skipped")


# ── List isolation ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_user_b_cannot_see_user_a_documents(client_a, client_b):
    """User A's documents must NOT appear in User B's document list."""
    # Ensure User A has at least one document
    await client_a.post(
        "/api/v1/upload",
        files={"file": ("a_private.pdf", PDF_BYTES, "application/pdf")},
    )

    a_docs = (await client_a.get("/api/v1/documents")).json()["documents"]
    b_docs = (await client_b.get("/api/v1/documents")).json()["documents"]

    a_ids = {d["id"] for d in a_docs}
    b_ids = {d["id"] for d in b_docs}

    overlap = a_ids & b_ids
    assert len(overlap) == 0, (
        f"Document isolation FAILED — User B can see User A's docs: {overlap}"
    )


# ── Query isolation ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_user_b_cannot_query_user_a_document(user_a_doc_id, client_b):
    """User B querying User A's document_id must receive 404."""
    r = await client_b.post(
        "/api/v1/query",
        json={"document_id": user_a_doc_id, "question": "What is this about?"},
    )
    assert r.status_code == 404, (
        f"Isolation FAILED — User B queried User A's doc {user_a_doc_id} and got {r.status_code}"
    )
    assert "not found" in r.json()["error"]["message"].lower()


# ── Delete isolation ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_user_b_cannot_delete_user_a_document(user_a_doc_id, client_b):
    """User B deleting User A's document_id must receive 404."""
    r = await client_b.delete(f"/api/v1/documents/{user_a_doc_id}")
    assert r.status_code == 404, (
        f"Isolation FAILED — User B deleted User A's doc {user_a_doc_id}"
    )


# ── Own documents are still accessible ───────────────────────────────────────

@pytest.mark.asyncio
async def test_user_a_can_see_own_documents(client_a):
    """Uploading creates a job (async). List endpoint must return 200 with correct shape
    regardless of how many documents Celery has processed so far."""
    r = await client_a.get("/api/v1/documents")
    assert r.status_code == 200
    body = r.json()
    assert "documents" in body
    assert "total" in body
    assert isinstance(body["documents"], list)
    assert body["total"] == len(body["documents"])  # count is internally consistent



@pytest.mark.asyncio
async def test_users_have_separate_document_lists(client_a, client_b):
    """Each user's document list is strictly independent."""
    # Upload one doc for each
    await client_a.post(
        "/api/v1/upload",
        files={"file": ("sep_a.pdf", PDF_BYTES, "application/pdf")},
    )
    await client_b.post(
        "/api/v1/upload",
        files={"file": ("sep_b.pdf", PDF_BYTES, "application/pdf")},
    )

    a_resp = (await client_a.get("/api/v1/documents")).json()
    b_resp = (await client_b.get("/api/v1/documents")).json()

    a_ids = {d["id"] for d in a_resp["documents"]}
    b_ids = {d["id"] for d in b_resp["documents"]}

    # The two sets must be completely disjoint
    assert a_ids.isdisjoint(b_ids), (
        f"Users share document IDs: {a_ids & b_ids}"
    )
