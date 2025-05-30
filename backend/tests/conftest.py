import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient
from tortoise.contrib.fastapi import register_tortoise
import os

# Import your FastAPI app instance from main.py
# Adjust the import path if your app instance is named differently or located elsewhere
from backend.main import app as actual_app
# Import the TORTOISE_ORM_CONFIG from main.py (or wherever it's defined)
from backend.main import TORTOISE_ORM_CONFIG

# Modify TORTOISE_ORM_CONFIG for testing (e.g., use an in-memory SQLite DB)
# It's crucial that the test database is different from the development/production DB
TEST_DB_URL = os.getenv("TORTOISE_TEST_DB", "sqlite://:memory:")

# Create a version of the config for testing
# Ensure models are correctly referenced for test environment
# The models list in TORTOISE_ORM_CONFIG might need adjustment if it uses relative paths
# that don't work the same way in test context, but "backend.models" should be fine.
MODELS_FOR_TEST = TORTOISE_ORM_CONFIG["apps"]["models"]["models"]


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest.fixture(scope="session")
async def app_for_testing() -> FastAPI:
    # This is where you'd initialize your app for testing
    # It's important to use a separate DB for tests
    # The actual_app is imported, so we are testing the real application instance

    # register_tortoise will use the TORTOISE_ORM_CONFIG from actual_app by default
    # We need to ensure it's configured for tests *before* the app starts if possible,
    # or ensure register_tortoise is called with a test-specific config.
    # FastAPI's dependency overrides or app state can be used.

    # For simplicity, we'll re-register Tortoise here for the test app instance
    # This assumes the main app's register_tortoise call won't interfere or has already run
    # with a non-test DB. Ideally, app configuration is flexible enough for this.

    # A common pattern is to have a create_app function that takes settings.
    # If not, we can try to modify the app's TORTOISE_ORM settings if it's stored in app.state
    # Or, more directly, ensure register_tortoise is called with test config.

    # The current TORTOISE_ORM_CONFIG in main.py uses "sqlite://./tiny_sales.sqlite3"
    # We need to override this for tests.

    test_specific_orm_config = {
        "connections": {"default": TEST_DB_URL},
        "apps": {
            "models": {
                "models": MODELS_FOR_TEST, # e.g., ["backend.models", "aerich.models"]
                "default_connection": "default",
            }
        },
        "use_tz": False, # Explicitly set for consistency in tests
        "timezone": "UTC" # Explicitly set for consistency in tests
    }

    register_tortoise(
        actual_app, # Use the imported app
        config=test_specific_orm_config,
        generate_schemas=True, # Generate schemas in the test DB
        add_exception_handlers=True, # Add Tortoise ORM specific exception handlers
    )
    # The original register_tortoise in main.py might run with the dev DB.
    # This call reconfigures it for the test client.
    # This setup is a bit tricky; ensuring DB isolation is key.
    # A better way is to have the main app's Tortoise init be more flexible
    # or delay it until after test setup can override settings.

    # For now, we assume this re-registration works for the test session.
    # Yielding the app is common for pytest-asyncio with FastAPI
    yield actual_app

    # Teardown:
    # Tortoise connections are usually managed by register_tortoise context manager
    # or explicitly closed. For in-memory DB, it's often dropped when connection closes.


@pytest.fixture(scope="function") # function scope for client to get clean state per test
async def client(app_for_testing: FastAPI):
    # This client will use the app with the test DB config
    async with TestClient(app_for_testing) as tc:
        yield tc
