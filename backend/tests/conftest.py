from typing import Generator, Any
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from tortoise.contrib.fastapi import register_tortoise
from tortoise.contrib.test import MEMORY_SQLITE
import os

# Import your FastAPI app instance from main.py
from ..main import app as actual_app

# Use an in-memory SQLite database for tests by default
TEST_DB_URL = os.getenv("TORTOISE_TEST_DB", MEMORY_SQLITE)


@pytest.fixture(scope="session")
def anyio_backend():
    # Required for pytest-asyncio to run async tests
    return "asyncio"

@pytest.fixture(scope="session")
async def app_for_testing() -> FastAPI:
    """
    Provides a FastAPI application instance configured for testing.
    This fixture is session-scoped, meaning the app and DB setup
    occur once per test session.
    """
    test_orm_config = {
        "connections": {"default": TEST_DB_URL},
        "apps": {
            "models": {
                "models": ["backend.models"],
                "default_connection": "default",
            }
        },
        # Optional: Explicitly set timezone handling for tests if needed
        # "use_tz": False,
        # "timezone": "UTC",
    }

    # Initialize Tortoise ORM for the test session on the actual app instance
    # This effectively reconfigures the database connection for the app during tests.
    register_tortoise(
        actual_app,
        config=test_orm_config,
        generate_schemas=True,  # Create DB schema in the test database
        add_exception_handlers=True,
    )
    yield actual_app
    # Teardown, like closing connections, is handled by Tortoise's context management
    # when the app shuts down or register_tortoise context ends.
    # For sqlite://:memory:, the database is ephemeral and lost on connection close.

@pytest.fixture(scope="function")
def client(app_for_testing: FastAPI) -> Generator[TestClient, Any, None]:
    """
    Provides an starlette TestClient for making requests to the test application.
    This client is function-scoped, so each test gets a fresh client,
    but it operates on the session-scoped app and database.
    """
    with TestClient(app_for_testing) as tc:
        yield tc
