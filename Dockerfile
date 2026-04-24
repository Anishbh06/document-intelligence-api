FROM python:3.11-slim

WORKDIR /app

# Install system dependencies if needed (e.g., for certain PDF libraries)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ensure the start script is executable
RUN chmod +x migrations/env.py

EXPOSE 10000

# The "All-in-One" Free Tier Command:
# 1. Force drops old tables (to fix the v1 to v3 collision)
# 2. Runs migrations (alembic upgrade head)
# 3. Starts the API + Worker
CMD ["sh", "-c", "python -c \"from app.db.session import engine; from sqlalchemy import text; with engine.connect() as conn: conn.execute(text('DROP TABLE IF EXISTS document_chunks, documents, jobs, users CASCADE;')); conn.commit(); print('Clean slate achieved!')\" && alembic upgrade head && (python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000} & celery -A app.celery_app worker --loglevel=info --concurrency=1)"]