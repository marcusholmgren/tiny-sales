# Tiny-Sales (Agent Instructions)

A modular prototype for order management built with FastAPI, Tortoise-ORM, `svix-ksuid`, and `uv`. Used as a sandbox for backend design patterns.

## Development Workflows

- **Run Dev Server**: `uv run fastapi dev`
- **Run All Tests**: `uv run pytest`
- **Run Single Test**: `uv run pytest src/app/features/<feature>/test_<name>.py`
- **Lint & Format**: `uv run ruff check . && uv run ruff format .`
- **CLI Commands**: `uv run manage-users --help` (or `uv run python -m app.cli.main`)

## Architecture & Code Conventions

- **Module Isolation**: Features live under `src/app/features/<feature>/`. Each feature encapsulates its own schemas, models, and service layer. Cross-feature dependencies must pass through domain interfaces or shared definitions in `src/app/common/`.
- **Primary Keys**: Use KSUIDs (`svix-ksuid`) for public and database IDs. Assign defaults at the model definition level.
- **Async Pattern**: Native `async`/`await` throughout. Do not execute blocking sync I/O inside endpoint handlers or services.
- **Typing**: Use standard Python type hinting (e.g., `list[str]`, `str | None`).

## Testing Standards

- **Runner**: `pytest-asyncio` only (`asyncio_mode = "auto"`).
- **FORBIDDEN**: Do not import or mark tests with `anyio`.
- **Database Fixtures**: Always use the `initialize_test_db` fixture from `conftest.py`. Never initialize `Tortoise.init()` inside isolated test cases to prevent event loop connection leakage.
