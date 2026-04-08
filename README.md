# Document Intelligence API (v1)

Production-ready RAG API for PDF document Q&A using FastAPI, PostgreSQL + pgvector, and Gemini (embeddings + generation).

This is the **v1 stable baseline**. Redis + Celery are planned for v2.

## What It Does

- Upload a PDF and extract text.
- Clean and chunk text into semantic units.
- Generate embeddings for each chunk with Gemini.
- Store chunks + vectors in PostgreSQL (pgvector).
- Query a document with semantic search and grounded answer generation.
- Return citations for traceability.

## Tech Stack

- `FastAPI` (async API)
- `SQLAlchemy` + `asyncpg` (database layer)
- `PostgreSQL` + `pgvector` (vector similarity search)
- `PyPDF` (PDF text extraction)
- `Gemini API`
  - `gemini-embedding-001` for embeddings
  - `gemini-2.5-flash` for answer generation
- `Docker` + `docker-compose`
- `pytest` + `httpx` (API tests)

## Project Structure

```text
app/
  api/routes/
    upload.py          # POST /api/v1/upload
    query.py           # POST /api/v1/query
  db/
    session.py         # DB engine/session
    init_db.py         # creates vector extension + tables
  models/
    document.py        # documents + document_chunks
  repositories/
    document_repo.py   # DB operations
  schemas/
    document.py        # request/response models
  services/
    pdf_service.py
    embedding_service.py
    rag_service.py
  tests/
main.py
```

## API Overview

Base URL:

- Local: `http://localhost:8000`
- Docs: `http://localhost:8000/docs`
- Health: `GET /health`

### 1) Upload PDF

`POST /api/v1/upload`  
`multipart/form-data` with `file`

Rules:

- Only `.pdf` allowed
- Max file size: 10 MB

Example:

```bash
curl -X POST "http://localhost:8000/api/v1/upload" \
  -F "file=@sample.pdf"
```

Sample response:

```json
{
  "message": "Document uploaded and processed successfully",
  "document": {
    "id": 1,
    "filename": "sample.pdf",
    "created_at": "2026-04-08T10:00:00.000000Z",
    "chunk_count": 7
  }
}
```

### 2) Query Document

`POST /api/v1/query`

Request:

```json
{
  "document_id": 1,
  "question": "What is this document about?"
}
```

Example:

```bash
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d "{\"document_id\":1,\"question\":\"What is this document about?\"}"
```

Sample response:

```json
{
  "answer": "The document discusses ...",
  "citations": [
    {
      "id": 11,
      "chunk_index": 0,
      "content": "..."
    }
  ]
}
```

## Environment Variables

Create `.env` from `.env.example`:

```env
# Gemini API key
GEMINI_API_KEY=your-gemini-api-key

# Database URL
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/doc_intelligence

# App
APP_ENV=development
SECRET_KEY=your-secret-key
```

## Run With Docker (Recommended)

1. Create `.env` file.
2. Start services:

```bash
docker compose up --build
```

This starts:

- `db` on `localhost:5432` (pgvector enabled)
- `api` on `localhost:8000`

## Run Locally (Without Docker)

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Ensure PostgreSQL + pgvector are available.
3. Set `DATABASE_URL` for local DB, for example:

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/doc_intelligence
```

4. Start API:

```bash
uvicorn app.main:app --reload
```

On startup, the app initializes:

- `CREATE EXTENSION IF NOT EXISTS vector`
- all SQLAlchemy tables

## Testing

Run all tests:

```bash
pytest -q
```

Current test coverage includes:

- upload happy path and validation
- query happy path and response shape
- not-found and request validation cases

## Current Processing Flow

1. Client uploads PDF.
2. API extracts raw text from pages.
3. Text is cleaned and split into chunks.
4. Chunk embeddings are generated.
5. Chunks + vectors are stored in `document_chunks`.
6. Query embedding is generated for user question.
7. Top-k similar chunks are retrieved by cosine distance.
8. Gemini generates grounded answer from retrieved context.

## Known Limitations in v1

- Embedding generation is sequential per chunk (higher latency for large PDFs).
- Upload processing happens inline in the request lifecycle.
- No distributed task queue yet.
- No caching layer yet.

These are expected and will be addressed in v2 with Redis + Celery.

## v2 Direction (Planned): Redis + Celery

Planned upgrades:

- Move document processing to Celery background jobs.
- Use Redis as Celery broker/result backend.
- Add async processing status endpoints.
- Optional Redis caching for repeated queries or embeddings.

Suggested future endpoints:

- `POST /api/v1/upload` -> returns `task_id` immediately
- `GET /api/v1/tasks/{task_id}` -> `PENDING | STARTED | SUCCESS | FAILURE`
- `GET /api/v1/documents/{id}` -> processing + metadata state

## Security and Production Notes

- Keep `.env` and API keys out of version control.
- Add request rate limiting before public exposure.
- Add auth (JWT/API key) for multi-tenant use.
- Add structured logging and error monitoring.
- Add DB migrations (`alembic`) for controlled schema changes.

## License

No license file is currently defined in this repository.
