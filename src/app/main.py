import os
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from tortoise import generate_config
from tortoise.contrib.fastapi import register_tortoise, tortoise_exception_handlers

from .core.logging_config import app_logger # Ensure app_logger is imported to initialize logging

# Assuming your routers and models are structured to be imported like this.
# This might require tiny-sales/backend to be in PYTHONPATH or specific run configurations.
# If 'routers' is a sub-package of 'backend', relative import is safer:
from .features.inventory.router import router as inventory_router
from .features.orders.router import router as orders_router
from .features.auth.router import router as auth_router
from .features.reports.router import router as reports_router
# from routers import inventory
# from routers import orders as orders_router
# from routers import auth as auth_router # Import the new auth router
# from routers import reports as reports_router # New import

logger = logging.getLogger("app.main") # This logger will inherit from 'app'

# TORTOISE_ORM_CONFIG
# Ensure the 'models' path is correct for your setup.
# If running uvicorn from 'tiny-sales/backend/', "models" might work.
# If running from 'tiny-sales/', and 'backend' is a package, "backend.models" is safer.
# Aerich configuration in pyproject.toml or aerich.ini should align with this.
TORTOISE_ORM_CONFIG = {
    "connections": {
        "default": "sqlite://./tiny_sales.sqlite3" # DB will be in the CWD of the app process
    },
    "apps": {
        "models": { # This is an app label, can be anything
            "models": [
                "app.features.auth.models",
                "app.features.inventory.models",
                "app.features.orders.models",
                # "app.common.models",
                "aerich.models"   # For Aerich migrations
            ],
            "default_connection": "default",
        }
    },
    # "timezone": "UTC", # Optional: if you want Tortoise to handle timezones
}

app = FastAPI(
    title="Tiny Sales API",
    description="API for managing orders and inventory.",
    version="0.1.0",
    exception_handlers=tortoise_exception_handlers(),
)

@asynccontextmanager
async def lifespan_test(api_app: FastAPI) -> AsyncGenerator[None, None]:
    config = generate_config(
        os.getenv("TORTOISE_TEST_DB", "sqlite://:memory:"),
        app_modules={"models": ["models"]},
        testing=True,
        connection_label="models",
    )
    async with register_tortoise(
        app=api_app,
        config=config,
        generate_schemas=True,
        _create_db=True,
    ):
        # db connected
        yield
        # app teardown
    # db connections closed
    # await Tortoise._drop_databases()


@asynccontextmanager
async def lifespan(api_app: FastAPI) -> AsyncGenerator[None, None]:
    if getattr(api_app.state, "testing", None):
        async with lifespan_test(app) as _:
            yield
    else:
        # app startup
        # async with register_orm(api_app):
            # db connected
        yield
            # app teardown
        # db connections closed

@app.get("/")
async def read_root(request: Request):
    """
    Root endpoint for the API.
    """
    client_host = request.client.host if request.client else "unknown client"
    logger.info(f"Root endpoint '/' accessed by {client_host}")
    return {"message": "Welcome to the Tiny Sales API!"}

# Include your routers
app.include_router(inventory_router, prefix="/api/v1")
app.include_router(orders_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1") # Add the auth router
app.include_router(reports_router, prefix="/api/v1") # Add the reports router


logger.info("Full path to sqlite db: %s", os.path.abspath(TORTOISE_ORM_CONFIG["connections"]["default"].split("://")[-1].strip("./")))

# Register Tortoise ORM with the FastAPI application
# This will initialize Tortoise, set up database connections.
# generate_schemas=True is useful for initial dev, but for production,
# rely on Aerich migrations. Set to False once initial schema is stable and managed by Aerich.
register_tortoise(
    app,
    config=TORTOISE_ORM_CONFIG,
    generate_schemas=False,  # Consider setting to False if Aerich handles all schema changes
    add_exception_handlers=True,  # Adds Tortoise ORM specific exception handlers
)
