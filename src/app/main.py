import os
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from tortoise import Tortoise
from tortoise.contrib.fastapi import tortoise_exception_handlers


from .features.inventory.router import router as inventory_router
from .features.orders.router import router as orders_router
from .features.auth.router import router as auth_router
from .features.reports.router import router as reports_router

logger = logging.getLogger("app.main")  # This logger will inherit from 'app'

TORTOISE_ORM_CONFIG = {
    "connections": {
        "default": os.getenv("DATABASE_URL", "sqlite://./tiny_sales.sqlite3")
    },
    "apps": {
        "models": {  # This is an app label, can be anything
            "models": [
                "app.features.auth.models",
                "app.features.inventory.models",
                "app.features.orders.models",
                "aerich.models",  # For Aerich migrations
            ],
            "default_connection": "default",
        }
    },
}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan context manager.

    Handles startup and shutdown events, such as connecting to the database.
    """
    logger.info("Starting application...")
    await Tortoise.init(config=TORTOISE_ORM_CONFIG)
    logger.info("Tortoise-ORM has been initialized.")

    yield

    await Tortoise.close_connections()
    logger.info("Tortoise-ORM connections have been closed.")


app = FastAPI(
    title="Tiny Sales API",
    description="API for managing orders and inventory.",
    version="0.1.0",
    exception_handlers=tortoise_exception_handlers(),
    lifespan=lifespan,
)


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
app.include_router(auth_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
