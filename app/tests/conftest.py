import pytest
from app.db.init_db import init_db

@pytest.fixture(scope="session", autouse=True)
async def setup_db():
    await init_db()