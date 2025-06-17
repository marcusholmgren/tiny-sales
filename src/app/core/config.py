import os

# In a real app, load from environment variables or a config file
SECRET_KEY: str = os.getenv(
    "SECRET_KEY", "your-secret-key-for-jwt-!ChangeMe!"
)  # TODO: Use a strong, environment-based secret
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# Example of other potential configurations:
# DATABASE_URL = os.getenv("DATABASE_URL", "sqlite://./tiny_sales.sqlite3")
# DEBUG_MODE = os.getenv("DEBUG_MODE", "False").lower() in ("true", "1", "t")
