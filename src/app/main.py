import os
import sys
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from tortoise import generate_config
from tortoise.contrib.fastapi import register_tortoise, tortoise_exception_handlers


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


# Configure basic logging
# For production, consider a more robust logging setup (e.g., structured logging, log rotation)

class NamespaceFilter(logging.Filter):
    def __init__(self, allowed_namespaces=None):
        super().__init__()
        self.allowed_namespaces = allowed_namespaces if allowed_namespaces is not None else []

    def filter(self, record):
        if not self.allowed_namespaces:
            return True # If no namespaces are specified, allow all records
        # Allow record if its name starts with any of the allowed namespaces
        return any(record.name.startswith(ns) for ns in self.allowed_namespaces)

log_formatter = logging.Formatter(
    fmt="%(asctime)s - %(name)s:%(lineno)d - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

app_logger = logging.getLogger("app")
app_logger.setLevel(logging.INFO)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_formatter)

# --- Namespace-based Filter (Optional) ---
# To only allow logs from specific top-level namespaces.
# For example, to only see logs from "app.features" and "app.main":
#
# allowed_log_namespaces = ["app.features", "app.main"]
# namespace_filter = NamespaceFilter(allowed_log_namespaces)
# console_handler.addFilter(namespace_filter)
#
# If `allowed_log_namespaces` is empty or None, the filter will allow all logs.
# This can be driven by environment variables for more dynamic control.
# For now, it's commented out to not break existing logging behavior
# until explicitly configured by the user.
app_logger.addHandler(console_handler)

logger = logging.getLogger("app.main")

# --- Namespace-specific logging level configuration examples ---
# To set a different level for a specific part of the application:
# For example, to see DEBUG messages from the 'orders' feature:
logging.getLogger("app.features.orders").setLevel(logging.DEBUG)

# And perhaps less verbose logging for another part:
# logging.getLogger("app.features.inventory").setLevel(logging.WARNING)

# Note: For these configurations to take effect, modules must use
# logging.getLogger(__name__) which will create loggers like
# "app.features.orders.router" or "app.services.some_service".
# These child loggers will inherit levels from their parents (e.g., "app.features.orders")
# or the application's root logger ("app") if not specifically set.



# sh = logging.StreamHandler(sys.stdout)
# sh.setLevel(logging.DEBUG)
# sh.setFormatter(fmt)
# # will print debug sql
# logger_db_client = logging.getLogger("tortoise.db_client")
# logger_db_client.setLevel(logging.DEBUG)
# # logger_db_client.addHandler(sh)
#
# logger_tortoise = logging.getLogger("tortoise")
# logger_tortoise.setLevel(logging.DEBUG)
# # logger_tortoise.addHandler(sh)

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
