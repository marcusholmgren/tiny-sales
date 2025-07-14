"""
Root conftest for the pytest test suite.

This file contains the main fixtures that are used across the entire test suite.

This setup uses a manual, async-native approach to database initialization
to ensure that each test runs against a fresh, isolated in-memory database,
which is the most reliable method for an async pytest environment.

Key Fixtures:
- `anyio_backend`: Specifies the asyncio backend for pytest-asyncio.
- `initialize_test_db`: (autouse) Creates a fresh DB schema for each test.
- `app_for_testing`: Provides the FastAPI application instance with its production
  lifespan disabled to allow `initialize_test_db` to manage the test DB.
- `client`: Provides a non-authenticated TestClient.
- `admin_client`: Provides a TestClient authenticated as a new admin user.
- `customer_client`: Provides a TestClient authenticated as a new customer user.
- `test_user_admin_token`: Creates an admin user and returns their auth token and user object.
- `test_user_customer_token`: Creates a customer user and returns their auth token and user object.
"""

from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Generator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from tortoise import Tortoise

from app.features.auth.models import User
from app.features.auth.security import get_password_hash

# Import the app
from app.main import app as actual_app


async def add_admin_user():
    admin_username = "adminfixture"
    admin_password = "adminpassword123"
    hashed_password = get_password_hash(admin_password)

    admin_user = await User.create(
        username=admin_username,
        email="adminfixture@example.com",
        hashed_password=hashed_password,
        role="admin",
    )
    return admin_user


async def add_customer_user():
    customer_username = "customerfixture"
    customer_password = "customerpassword123"
    hashed_password = get_password_hash(customer_password)

    customer_user = await User.create(
        username=customer_username,
        email="customerfixture@example.com",
        hashed_password=hashed_password,
        role="customer",
    )
    return customer_user


async def add_report_user():
    username = "reportscustomer"
    password = "password123"
    hashed_password = get_password_hash(password)

    user = await User.create(
        username=username,
        email="reportscustomer@example.com",
        hashed_password=hashed_password,
        role="customer",
    )
    return user


async def add_report_admin():
    username = "reportsadmin"
    password = "password123"
    hashed_password = get_password_hash(password)

    user = await User.create(
        username=username,
        email="reportsadmin@example.com",
        hashed_password=hashed_password,
        role="admin",
    )
    return user


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    """
    Specifies the asyncio backend for pytest-asyncio.
    """
    return "asyncio"


@pytest_asyncio.fixture(scope="function", autouse=True)
async def initialize_test_db() -> AsyncGenerator[None, None]:
    """
    Initializes the database for each test function.

    This async, autouse fixture creates a fresh in-memory database and schema
    for each test and tears it down afterwards.
    """
    test_db_config = {
        "connections": {"default": "sqlite://:memory:"},
        "apps": {
            "models": {
                "models": [
                    "app.features.auth.models",
                    "app.features.inventory.models",
                    "app.features.orders.models",
                    "aerich.models",
                ],
                "default_connection": "default",
            }
        },
    }
    await Tortoise.init(config=test_db_config)
    await Tortoise.generate_schemas()
    await add_customer_user()
    await add_admin_user()
    await add_report_user()
    await add_report_admin()

    yield

    await Tortoise.close_connections()


@pytest.fixture(scope="function")
def app_for_testing() -> Generator[FastAPI, Any, None]:
    """
    Provides a FastAPI application instance for testing, with its
    production lifespan manager disabled to allow the test DB fixture
    to manage the database connection.
    """
    original_lifespan = actual_app.router.lifespan_context

    @asynccontextmanager
    async def dummy_lifespan(app: FastAPI):
        yield

    actual_app.router.lifespan_context = dummy_lifespan

    yield actual_app

    # Restore the original lifespan context after the test
    actual_app.router.lifespan_context = original_lifespan


@pytest.fixture(scope="function")
def client(app_for_testing: FastAPI) -> Generator[TestClient, Any, None]:
    """
    Provides a non-authenticated starlette TestClient.
    """
    with TestClient(app_for_testing) as tc:
        yield tc


@pytest_asyncio.fixture(scope="function")
async def admin_client(app_for_testing: FastAPI) -> AsyncGenerator[TestClient, Any]:
    """
    Provides a TestClient authenticated as a new admin user.
    Cleans up the user afterwards.
    """
    admin_username = "adminfixture"
    admin_password = "adminpassword123"
    # hashed_password = get_password_hash(admin_password)

    # admin_user = await User.create(
    #     username=admin_username,
    #     email="adminfixture@example.com",
    #     hashed_password=hashed_password,
    #     role="admin",
    # )

    with TestClient(app_for_testing) as tc:
        response = tc.post(
            "/api/v1/auth/token",
            data={"username": admin_username, "password": admin_password},
        )
        if response.status_code != 200:
            raise Exception(f"Admin authentication failed for {admin_username}")

        token_data = response.json()
        auth_token = token_data["access_token"]

        tc.headers = {"Authorization": f"Bearer {auth_token}"}
        yield tc

    # await admin_user.delete()


@pytest_asyncio.fixture(scope="function")
async def customer_client(app_for_testing: FastAPI) -> AsyncGenerator[TestClient, Any]:
    """
    Provides a TestClient authenticated as a new customer user.
    Cleans up the user afterwards.
    """
    customer_username = "customerfixture"
    customer_password = "customerpassword123"
    # hashed_password = get_password_hash(customer_password)

    # customer_user = await User.create(
    #     username=customer_username,
    #     email="customerfixture@example.com",
    #     hashed_password=hashed_password,
    #     role="customer",
    # )

    with TestClient(app_for_testing) as tc:
        response = tc.post(
            "/api/v1/auth/token",
            data={"username": customer_username, "password": customer_password},
        )
        if response.status_code != 200:
            raise Exception(f"Customer authentication failed for {customer_username}")

        token_data = response.json()
        auth_token = token_data["access_token"]

        tc.headers = {"Authorization": f"Bearer {auth_token}"}
        yield tc

    # await customer_user.delete()


@pytest_asyncio.fixture(scope="function")
async def test_user_admin_token(
    app_for_testing: FastAPI,
) -> AsyncGenerator[tuple[str, User], Any]:
    """
    Creates an admin user, gets their token, and yields (token, user_object).
    Cleans up the user afterwards.
    """
    username = "reportsadmin"
    password = "password123"
    # hashed_password = get_password_hash(password)

    # user = await User.create(
    #     username=username,
    #     email="reportsadmin@example.com",
    #     hashed_password=hashed_password,
    #     role="admin",
    # )
    user = await User.get(username=username)

    with TestClient(app_for_testing) as tc:
        response = tc.post(
            "/api/v1/auth/token", data={"username": username, "password": password}
        )
        if response.status_code != 200:
            await user.delete()
            raise Exception(f"Could not get token for {username}")
        auth_token = response.json()["access_token"]

    yield auth_token, user

    # await user.delete()


@pytest_asyncio.fixture(scope="function")
async def test_user_customer_token(
    app_for_testing: FastAPI,
) -> AsyncGenerator[tuple[str, User], Any]:
    """
    Creates a customer user, gets their token, and yields (token, user_object).
    Cleans up the user afterwards.
    """
    username = "reportscustomer"
    password = "password123"
    # hashed_password = get_password_hash(password)

    # user = await User.create(
    #     username=username,
    #     email="reportscustomer@example.com",
    #     hashed_password=hashed_password,
    #     role="customer",
    # )
    user = await User.get(username=username)

    with TestClient(app_for_testing) as tc:
        response = tc.post(
            "/api/v1/auth/token", data={"username": username, "password": password}
        )
        if response.status_code != 200:
            await user.delete()
            raise Exception(f"Could not get token for {username}")
        auth_token = response.json()["access_token"]

    yield auth_token, user

    # await user.delete()
