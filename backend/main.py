import os
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from fastapi import FastAPI
from tortoise import generate_config
from tortoise.contrib.fastapi import register_tortoise, tortoise_exception_handlers


# Assuming your routers and models are structured to be imported like this.
# This might require tiny-sales/backend to be in PYTHONPATH or specific run configurations.
# If 'routers' is a sub-package of 'backend', relative import is safer:
# from .routers import inventory
from .routers import inventory


# Configure basic logging
# For production, consider a more robust logging setup (e.g., structured logging, log rotation)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
                "backend.models", # Assuming 'tiny-sales' is in PYTHONPATH and 'backend' is a package.
                                  # Adjust if your execution context or Aerich config differs.
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
async def lifespan_test(app: FastAPI) -> AsyncGenerator[None, None]:
    config = generate_config(
        os.getenv("TORTOISE_TEST_DB", "sqlite://:memory:"),
        app_modules={"models": ["models"]},
        testing=True,
        connection_label="models",
    )
    async with register_tortoise(
        app=app,
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
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    if getattr(app.state, "testing", None):
        async with lifespan_test(app) as _:
            yield
    else:
        # app startup
        # async with register_orm(app):
            # db connected
        yield
            # app teardown
        # db connections closed

@app.get("/")
async def read_root():
    """
    Root endpoint for the API.
    """
    logger.info(f"Root endpoint '/' accessed by {app.client.host if app.client else 'unknown client'}")
    return {"message": "Welcome to the Tiny Sales API!"}

# Include your routers
app.include_router(inventory.router, prefix="/api/v1") # Example: Prefixing all inventory routes with /api/v1
# Add other routers here, e.g.:
# from .routers import orders
# app.include_router(orders.router, prefix="/api/v1")


# Register Tortoise ORM with the FastAPI application
# This will initialize Tortoise, set up database connections.
# generate_schemas=True is useful for initial dev, but for production,
# rely on Aerich migrations. Set to False once initial schema is stable and managed by Aerich.
register_tortoise(
    app,
    config=TORTOISE_ORM_CONFIG,
    generate_schemas=True,  # Consider setting to False if Aerich handles all schema changes
    add_exception_handlers=True,  # Adds Tortoise ORM specific exception handlers
)
