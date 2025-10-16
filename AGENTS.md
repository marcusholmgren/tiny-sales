# Tiny Sales

A little order management application with features
- auth
- inventory
- orders
- reports

## Technology

Built on top of FastAPI and Tortoise ORM and using uv for Python dependency management.

## Test database connection

You can test the database connection with the CLI command:
```bash
uv run src/app/cli/main.py test-db-connection
```
It will report if the connection is successful and how many users are in the database.


## Running unit tests

```bash
uv run pytest
```
