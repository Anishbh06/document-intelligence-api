import asyncio
from sqlalchemy import text
from app.db.session import engine

async def reset_database():
    print("🚀 [ASYNC] Attempting to wipe old tables for a clean v3 start...")
    try:
        async with engine.begin() as conn:
            # Drop tables in correct order of dependencies
            await conn.execute(text("DROP TABLE IF EXISTS document_chunks, documents, jobs, users CASCADE;"))
            print("✅ Clean slate achieved! All old tables dropped.")
    except Exception as e:
        print(f"⚠️ Note: Table drop skipped or failed: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(reset_database())
    except Exception as e:
        print(f"❌ Critical failure in reset script: {e}")
