from sqlalchemy import text
from app.db.session import engine

def reset_database():
    print("🚀 Attempting to wipe old tables for a clean v3 start...")
    try:
        with engine.connect() as conn:
            # Drop tables in correct order of dependencies
            conn.execute(text("DROP TABLE IF EXISTS document_chunks, documents, jobs, users CASCADE;"))
            conn.commit()
        print("✅ Clean slate achieved! All old tables dropped.")
    except Exception as e:
        print(f"⚠️ Note: Table drop skipped or failed (might already be empty): {e}")

if __name__ == "__main__":
    reset_database()
