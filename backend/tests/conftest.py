import os
import pytest

# Set environment variables at module level to ensure they are available
# before any other module is imported during test collection.
os.environ["BINANCE_API_KEY"] = "test_key"
os.environ["BINANCE_API_SECRET"] = "test_secret"
os.environ["DATABASE_URL"] = "postgresql://user:pass@localhost:5432/db"
os.environ["POSTGRES_USER"] = "user"
os.environ["POSTGRES_PASSWORD"] = "pass"
os.environ["POSTGRES_DB"] = "db"
os.environ["REDIS_HOST"] = "localhost"
os.environ["REDIS_PORT"] = "6379"

@pytest.fixture(scope="session", autouse=True)
def set_env_vars():
    # Keep this fixture just in case, or for any setup that needs to happen in a fixture context
    pass
