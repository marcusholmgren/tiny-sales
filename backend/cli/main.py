import asyncio
import typer
from tortoise import Tortoise, run_async
from tortoise.exceptions import IntegrityError, DoesNotExist
import os
import sys
from pathlib import Path

# Add project root to sys.path to allow absolute imports from 'backend'
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

# Now imports from 'backend' should work
from backend import models
from backend.auth import get_password_hash # To hash passwords
from backend.models import User # Explicit import for User model

# Replicate TORTOISE_ORM_CONFIG for the CLI
# Ensure this path is correct when running the CLI
# If CLI is run from project root, 'tiny_sales.sqlite3' is fine.
# If CLI is run from 'backend/cli', DB path might need adjustment like '../../tiny_sales.sqlite3'
# Using an absolute path via environment variable is often more robust.
DB_PATH = os.environ.get("DATABASE_URL", "sqlite://./tiny_sales.sqlite3")
if "sqlite" in DB_PATH and not DB_PATH.startswith("sqlite:////"): # if relative path for sqlite
    # Adjust relative path to be relative to project root if not absolute
    if not os.path.isabs(DB_PATH.split("sqlite://")[1]):
        DB_PATH = f"sqlite:///{project_root}/{DB_PATH.split('sqlite://')[1]}"


TORTOISE_ORM_CONFIG = {
    "connections": {
        "default": DB_PATH
    },
    "apps": {
        "models": {
            "models": [
                "backend.models", # Use fully qualified path
                "aerich.models"   # For Aerich migrations
            ],
            "default_connection": "default",
        }
    },
    "use_tz": False, # Explicitly set for Tortoise
    "timezone": "UTC" # Explicitly set for Tortoise
}

app = typer.Typer(name="tiny-sales-cli", help="CLI for managing Tiny Sales application data.")

# Shared async context manager for database connection
class DBConnection:
    async def __aenter__(self):
        # typer.echo("Initializing database connection...")
        await Tortoise.init(config=TORTOISE_ORM_CONFIG)
        # typer.echo(f"Database connection initialized with: {TORTOISE_ORM_CONFIG}")
        await Tortoise.generate_schemas(safe=True) # Generate schema if it doesn't exist
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # typer.echo("Closing database connection...")
        await Tortoise.close_connections()
        # typer.echo("Database connection closed.")

# User management commands
user_app = typer.Typer(name="users", help="Manage user accounts.")
app.add_typer(user_app)

@user_app.command("create-admin")
async def create_admin_user(
    username: str = typer.Option(..., prompt=True, help="Username for the new admin."),
    email: str = typer.Option(..., prompt=True, help="Email for the new admin."),
    password: str = typer.Option(..., prompt=True, hide_input=True, confirmation_prompt=True, help="Password for the new admin.")
):
    """Creates a new admin user."""
    async with DBConnection():
        typer.echo(f"Attempting to create admin user: {username} ({email})...")
        try:
            # Check if user already exists
            if await User.filter(username=username).exists():
                typer.secho(f"Error: User with username '{username}' already exists.", fg=typer.colors.RED)
                raise typer.Exit(code=1)
            if await User.filter(email=email).exists():
                typer.secho(f"Error: User with email '{email}' already exists.", fg=typer.colors.RED)
                raise typer.Exit(code=1)

            hashed_password = get_password_hash(password)
            admin_user = await User.create(
                username=username,
                email=email,
                hashed_password=hashed_password,
                role="admin",
                is_active=True
            )
            typer.secho(f"Admin user '{admin_user.username}' created successfully with ID: {admin_user.public_id}", fg=typer.colors.GREEN)
        except IntegrityError as e:
            # This is a fallback, specific checks above are preferred
            typer.secho(f"Error creating admin user: An integrity error occurred. This might be due to a duplicate username or email if not caught above. Details: {e}", fg=typer.colors.RED)
            raise typer.Exit(code=1)
        except Exception as e:
            typer.secho(f"An unexpected error occurred: {e}", fg=typer.colors.RED)
            raise typer.Exit(code=1)

@user_app.command("promote-to-admin")
async def promote_user_to_admin(
    username: str = typer.Argument(..., help="The username of the user to promote to admin.")
):
    """Promotes an existing user to the admin role."""
    async with DBConnection():
        typer.echo(f"Attempting to promote user '{username}' to admin...")
        try:
            user = await User.get_or_none(username=username)

            if not user:
                typer.secho(f"Error: User with username '{username}' not found.", fg=typer.colors.RED)
                raise typer.Exit(code=1)

            if user.role == "admin":
                typer.secho(f"User '{username}' is already an admin.", fg=typer.colors.YELLOW)
                raise typer.Exit(code=0)

            if not user.is_active:
                typer.secho(f"Error: User '{username}' is currently inactive. Activate the user before promoting to admin.", fg=typer.colors.RED)
                # Future: Add an option to activate and promote simultaneously.
                raise typer.Exit(code=1)

            user.role = "admin"
            await user.save()
            typer.secho(f"User '{username}' has been successfully promoted to admin.", fg=typer.colors.GREEN)

        except DoesNotExist: # Should be caught by get_or_none, but as a fallback
            typer.secho(f"Error: User with username '{username}' not found.", fg=typer.colors.RED)
            raise typer.Exit(code=1)
        except Exception as e:
            typer.secho(f"An unexpected error occurred: {e}", fg=typer.colors.RED)
            raise typer.Exit(code=1)

@user_app.command("disable-user")
async def disable_user_account(
    username: str = typer.Argument(..., help="The username of the user to disable.")
):
    """Disables an existing user's account."""
    async with DBConnection():
        typer.echo(f"Attempting to disable user account '{username}'...")
        try:
            user = await User.get_or_none(username=username)

            if not user:
                typer.secho(f"Error: User with username '{username}' not found.", fg=typer.colors.RED)
                raise typer.Exit(code=1)

            if not user.is_active:
                typer.secho(f"User '{username}' is already inactive.", fg=typer.colors.YELLOW)
                raise typer.Exit(code=0)

            user.is_active = False
            await user.save()
            typer.secho(f"User account '{username}' has been successfully disabled.", fg=typer.colors.GREEN)

        except DoesNotExist: # Fallback
            typer.secho(f"Error: User with username '{username}' not found.", fg=typer.colors.RED)
            raise typer.Exit(code=1)
        except Exception as e:
            typer.secho(f"An unexpected error occurred: {e}", fg=typer.colors.RED)
            raise typer.Exit(code=1)

@user_app.command("enable-user")
async def enable_user_account(
    username: str = typer.Argument(..., help="The username of the user to enable.")
):
    """Enables an existing user's account."""
    async with DBConnection():
        typer.echo(f"Attempting to enable user account '{username}'...")
        try:
            user = await User.get_or_none(username=username)

            if not user:
                typer.secho(f"Error: User with username '{username}' not found.", fg=typer.colors.RED)
                raise typer.Exit(code=1)

            if user.is_active:
                typer.secho(f"User '{username}' is already active.", fg=typer.colors.YELLOW)
                raise typer.Exit(code=0)

            user.is_active = True
            await user.save()
            typer.secho(f"User account '{username}' has been successfully enabled.", fg=typer.colors.GREEN)

        except DoesNotExist: # Fallback
            typer.secho(f"Error: User with username '{username}' not found.", fg=typer.colors.RED)
            raise typer.Exit(code=1)
        except Exception as e:
            typer.secho(f"An unexpected error occurred: {e}", fg=typer.colors.RED)
            raise typer.Exit(code=1)

# Placeholder for testing db connection (can be removed later)
@app.command("test-db-connection")
async def test_db_connection_command():
    """Tests the database connection and lists user models."""
    async with DBConnection():
        typer.echo("Successfully connected to the database.")
        try:
            user_count = await models.User.all().count()
            typer.echo(f"Found {user_count} user(s) in the database.")
            if user_count > 0:
                first_user = await models.User.first()
                typer.echo(f"First user: {first_user}")
        except Exception as e:
            typer.echo(f"Error querying users: {e}", err=True)

if __name__ == "__main__":
    # This structure allows async commands to be run by Typer
    app()
