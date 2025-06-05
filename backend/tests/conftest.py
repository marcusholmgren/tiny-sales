from typing import Generator, Any, AsyncGenerator
import pytest
import pytest_asyncio # Added import
from fastapi import FastAPI
from fastapi.testclient import TestClient
from tortoise.contrib.fastapi import register_tortoise
from tortoise.contrib.test import MEMORY_SQLITE
import os
from ..models import User, Order, OrderItem, OrderEvent, InventoryItem, Category # Added more models
from ..auth import get_password_hash # Changed import

# Import your FastAPI app instance from main.py
# from main import app as actual_app
from .. import main

# Use an in-memory SQLite database for tests by default
TEST_DB_URL = os.getenv("TORTOISE_TEST_DB", MEMORY_SQLITE)


@pytest.fixture(scope="session")
def anyio_backend():
    # Required for pytest-asyncio to run async tests
    return "asyncio"

@pytest_asyncio.fixture(scope="session")
async def app_for_testing() -> AsyncGenerator[FastAPI, Any]:
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
    # MOVED register_tortoise INTO the fixture setup phase
    
    # Using a separate app instance for test configuration to avoid state leakage
    # from main.app if it's globally modified.
    # However, the task implies main.app is the one to be tested.
    # Let's assume main.app should be configured for tests.
    
    _app = main.app # Use the actual app instance from main.py

    register_tortoise(
        _app, # Configure the app instance that will be used
        config=test_orm_config,
        generate_schemas=True,  # Create DB schema in the test database
        add_exception_handlers=True, # Add Tortoise exception handlers
    )
    yield _app # Yield the configured app
    
    # Teardown: Tortoise ORM connections are typically closed on app shutdown.
    # For in-memory SQLite, this might not be strictly necessary as data is lost,
    # but good practice for other DBs.
    # Tortoise's `shutdown_connections` can be called if explicit cleanup is needed here,
    # but usually register_tortoise handles this with FastAPI's lifespan events.
    # await Tortoise.close_connections() # Example if explicit close needed
    # For now, relying on Tortoise's integration with FastAPI lifespan.
    # For sqlite://:memory: the database is ephemeral and lost on connection close.

@pytest.fixture(scope="function")
def client(app_for_testing: FastAPI) -> Generator[TestClient, Any, None]:
    """
    Provides a starlette TestClient for making requests to the test application.
    This client is function-scoped, so each test gets a fresh client,
    but it operates on the session-scoped app and database.
    """
    username = "testuser"
    password = "testpassword123"
    email = "testuser@example.com"
    with TestClient(app_for_testing) as tc:
        # Register user (ignore if already exists)
        response = tc.post("/api/v1/auth/register", json={
            "username": username,
            "password": password,
            "email": email
        })
        # print(f"User registration response: {response.status_code} - {response.json()}") # Optional: suppress noisy output
        yield tc

@pytest_asyncio.fixture(scope="function")
async def admin_client(app_for_testing: FastAPI) -> Generator[TestClient, Any, None]:
    """
    Provides a TestClient authenticated as an admin user.
    """
    admin_username = "adminfixtureuser"
    admin_password = "adminpassword123"
    admin_email = "adminfixtureuser@example.com"
    hashed_password = get_password_hash(admin_password)

    # Create admin user directly in the database
    # Ensure this runs within the Tortoise ORM context provided by app_for_testing
    admin_user = await User.create(
        username=admin_username,
        email=admin_email,
        hashed_password=hashed_password,
        role="admin"  # Changed to string literal
    )

    with TestClient(app_for_testing) as tc:
        # Authenticate admin user
        response = tc.post("/api/v1/auth/token", data={
            "username": admin_username,
            "password": admin_password
        })
        if response.status_code != 200:
            # If auth fails, print response for debugging and raise an error
            print(f"Admin authentication failed: {response.status_code} - {response.json()}")
            raise Exception(f"Admin authentication failed for {admin_username}")
        
        token_data = response.json()
        auth_token = token_data["access_token"]
        
        # Set auth token for the client
        tc.headers = {
            "Authorization": f"Bearer {auth_token}"
        }
        yield tc
        # Clean up: delete the admin user after the test
        await admin_user.delete()

@pytest_asyncio.fixture(scope="function") # Added decorator
async def test_user_admin_token(app_for_testing: FastAPI) -> AsyncGenerator[tuple[str, User], Any]:
    """
    Creates an admin user, gets their token, and yields (token, user_object).
    Cleans up the user afterwards.
    """
    username = "reportsadminuser"
    password = "password123" # Standard password for test users
    email = "reportsadmin@example.com"
    hashed_password = get_password_hash(password)

    user = await User.create(
        username=username,
        email=email,
        hashed_password=hashed_password,
        role="admin"
    )

    auth_token = ""
    with TestClient(app_for_testing) as tc:
        response = tc.post("/api/v1/auth/token", data={"username": username, "password": password})
        if response.status_code != 200:
            await user.delete() # Clean up user if token fetching fails
            print(f"Failed to get token for {username}: {response.status_code} - {response.json()}")
            raise Exception(f"Could not get token for {username}")
        auth_token = response.json()["access_token"]
    
    yield auth_token, user
    
    await user.delete()

@pytest_asyncio.fixture(scope="function")
async def clean_db_each_test(app_for_testing: FastAPI): # Depends on app_for_testing to ensure DB is init
    # Delete data in reverse order of dependency or where CASCADE delete might not be fully effective
    await OrderItem.all().delete()
    await OrderEvent.all().delete()
    await Order.all().delete()
    await InventoryItem.all().delete()
    await Category.all().delete()
    # User table is cleaned by specific user token fixtures
    yield

@pytest_asyncio.fixture(scope="function") # Added decorator
async def test_user_customer_token(app_for_testing: FastAPI) -> AsyncGenerator[tuple[str, User], Any]:
    """
    Creates a customer user, gets their token, and yields (token, user_object).
    Cleans up the user afterwards.
    """
    username = "reportscustomeruser"
    password = "password123" # Standard password for test users
    email = "reportscustomer@example.com"
    hashed_password = get_password_hash(password)

    user = await User.create(
        username=username,
        email=email,
        hashed_password=hashed_password,
        role="customer" # Default role
    )

    auth_token = ""
    with TestClient(app_for_testing) as tc:
        response = tc.post("/api/v1/auth/token", data={"username": username, "password": password})
        if response.status_code != 200:
            await user.delete() # Clean up user if token fetching fails
            print(f"Failed to get token for {username}: {response.status_code} - {response.json()}")
            raise Exception(f"Could not get token for {username}")
        auth_token = response.json()["access_token"]

    yield auth_token, user
    
    await user.delete()
