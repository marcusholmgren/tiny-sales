from fastapi import FastAPI
from tortoise.contrib.fastapi import register_tortoise
import uvicorn

# This assumes that when the application runs, 'backend' is a package
# available in the Python path, or that the application is run from
# the directory containing 'backend'.
TORTOISE_ORM_CONFIG = {
    "connections": {
        # The database file will be created in the directory where the app is run.
        # If running from `backend/`, it will be `backend/tiny_sales.sqlite3`
        "default": "sqlite://./tiny_sales.sqlite3"
    },
    "apps": {
        "models": { # This is an app label, can be anything
            "models": [
                "models", # Path to your models module
                "aerich.models"   # For Aerich migrations (good practice)
            ],
            "default_connection": "default",
        }
    },
    # Optional: Add timezone if your application is timezone-aware
    # "timezone": "UTC",
}

app = FastAPI(
    title="Tiny Sales API",
    description="API for managing orders and inventory.",
    version="0.1.0",
)

@app.get("/")
async def read_root():
    """
    Root endpoint for the API.
    """
    return {"message": "Welcome to the Tiny Sales API!"}

# Register Tortoise ORM with the FastAPI application
# This will initialize Tortoise, set up database connections,
# and create tables based on the models if they don't exist.
register_tortoise(
    app,
    config=TORTOISE_ORM_CONFIG,
    generate_schemas=True,  # Automatically create database tables based on models
    add_exception_handlers=True,  # Add Tortoise ORM exception handlers
)

if __name__ == "__main__":
    # This allows running the app directly with `python backend/main.py`
    # The app will be served by uvicorn.
    # reload=True is useful for development.
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
