# Tiny Sales

A high-performance order management application prototype.

## Core Features

- **Authentication**: JWT-based auth with role-based access control (Admin/Customer).
- **Inventory**: Category management and stock tracking for products.
- **Orders**: Full lifecycle management (Creation -> Payment -> Shipping -> Cancellation).
- **Reports**: Business intelligence endpoints for sales, stock levels, and inventory value.

## Technology Stack

- **Framework**: FastAPI (Asynchronous Python)
- **Database**: Tortoise ORM (with `aiosqlite` for local dev/testing)
- **Dependency Management**: `uv`
- **Security**: `python-jose` (JWT), `bcrypt` (Hashing)
- **ID Generation**: `svix-ksuid` (K-Sortable Unique IDs)

## Project Structure

```text
src/app/
├── core/             # App configuration, DB setup, logging
├── common/           # Shared models and schemas
├── cli/              # Typer-based CLI for management tasks
└── features/         # Domain-driven features
    ├── auth/         # User management, login, security
    ├── inventory/    # Categories and items
    ├── orders/       # Order processing
    └── reports/      # Aggregated data and stats
```

## Management CLI

The project includes a CLI for administrative tasks. You can run it via `uv`:

```bash
# General help
uv run manage-users --help

# Create an initial admin user
uv run manage-users users create-admin

# Manage existing users
uv run manage-users users promote-to-admin <username>
uv run manage-users users disable-user <username>

# Test database connectivity
uv run manage-users test-db-connection
```

*Note: `manage-users` is an alias defined in `pyproject.toml`. You can also run the script directly: `uv run src/app/cli/main.py`.*

## Testing & Quality

### Async Testing Standards

**CRITICAL**: This project standardizes on `pytest-asyncio` with `asyncio_mode = "auto"`. 

- **Do NOT** use `anyio` markers.
- **Do NOT** mix different async event loops.
- **Why?** Tortoise ORM maintains global state on the event loop. Mixing runners causes orphaned connections (especially with SQLite) that prevent the test process from exiting cleanly in CI/CD.

### Running Tests

```bash
# Run all tests
uv run pytest

# Run a specific feature's tests
uv run pytest src/app/features/inventory/
```

Tests use a fresh in-memory SQLite database (`sqlite://:memory:`) for every test function, managed by the `initialize_test_db` fixture in `conftest.py`.
