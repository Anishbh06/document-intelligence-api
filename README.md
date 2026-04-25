# Document Intelligence API (v3.0.0) 🚀

A production-ready, multi-tenant RAG (Retrieval-Augmented Generation) system for PDF document analysis. Built with a modern distributed architecture for high performance and scalability.

**Watch the frontend UI Demo:** https://www.loom.com/share/8380ed4d4ef548418343beb349c47717

> 2-minute walkthrough showing PDF upload, Q&A with citations, and system architecture.


**Live Demo:** [https://project-7pe5b.vercel.app](https://project-7pe5b.vercel.app)  
**Backend API:** [https://document-intelligence-api.onrender.com/docs](https://document-intelligence-api.onrender.com/docs)

## ✨ New in v3.0.0
- **Multi-Tenancy:** Secure JWT-based authentication with per-user document isolation.
- **Distributed Processing:** Async PDF processing using **Celery** + **Redis (Upstash)**.
- **Modern Frontend:** Beautiful Next.js 14 dashboard with real-time job tracking.
- **Production Infrastructure:** Automated deployments to **Vercel** (Frontend) and **Render** (Backend).

## 🛠 Tech Stack

### Backend (Python/FastAPI)
- **FastAPI:** High-performance async web framework.
- **PostgreSQL + pgvector:** Vector similarity search for semantic retrieval.
- **SQLAlchemy + Alembic:** Database ORM and version-controlled migrations.
- **Celery + Redis:** Distributed task queue for background PDF processing.
- **Gemini API:** 
  - `text-embedding-004` for high-accuracy vectors.
  - `gemini-1.5-flash` for low-latency grounded generation.

### Frontend (Next.js/React)
- **Next.js 14:** App router, server-side rendering, and optimized builds.
- **Tailwind CSS:** Premium, responsive design system.
- **Lucide React:** Modern icon set.

## 🏗 System Architecture

```text
app/
  api/routes/
    auth.py            # User registration & JWT login
    upload.py          # Async PDF upload -> triggers Celery
    jobs.py            # Real-time task status tracking
    query.py           # Semantic search & Gemini generation
    documents.py       # Library management & deletion
  core/
    security.py        # Password hashing & JWT logic
    celery_app.py      # Task queue configuration
  models/              # SQLAlchemy schema (Users, Docs, Chunks, Jobs)
  services/            # Business logic (RAG, PDF parsing, Embeddings)
frontend/              # Next.js Application
```

## 🚀 Getting Started

### Local Development (Docker)

1. Clone the repo and create a `.env` file from the example.
2. Spin up the entire stack:
   ```bash
   docker-compose up --build
   ```
3. Access the Frontend at `http://localhost:3000` and API at `http://localhost:10000`.

### Production Deployment

- **Backend:** Deploy to **Render** as a Web Service. Ensure `DATABASE_URL` (Postgres) and `REDIS_URL` (Upstash) are set.
- **Frontend:** Deploy to **Vercel**. Set `NEXT_PUBLIC_API_URL` to your Render service address.

## 🔐 Security & Multi-Tenancy

Each user can only see and query their own documents. Authentication is handled via **JWT (JSON Web Tokens)** stored securely in the browser. 
- All passwords are salted and hashed using **Bcrypt**.
- CORS is strictly configured to only allow your specific Vercel production domain.

## 📈 Processing Flow

1. **Upload:** User sends a PDF. The API returns a `job_id` instantly.
2. **Background:** Celery picks up the task, extracts text, generates embeddings, and stores them in PostgreSQL.
3. **Tracking:** Frontend polls the status until "completed".
4. **Query:** User asks a question. The system finds the most relevant chunks in the vector DB and uses Gemini to generate a response grounded *only* in those chunks.

## 📜 License
This project is for educational and portfolio purposes. All rights reserved.
