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
# 1. Reset old tables (one-time v1→v3 migration)
# 2. Run Alembic migrations
# 3. Start Celery worker in background (its crash won't kill the API)
# 4. Start uvicorn as the MAIN foreground process (keeps container alive)
CMD ["sh", "-c", "python -m app.db.reset_db && alembic upgrade head && celery -A app.celery_app worker --loglevel=info --concurrency=1 & python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
