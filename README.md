# Tiny sales

[![Run Pytest](https://github.com/marcusholmgren/tiny-sales/actions/workflows/pytest.yml/badge.svg)](https://github.com/marcusholmgren/tiny-sales/actions/workflows/pytest.yml)

This project is a simple little sales and inventory API system.
It has inventory management for products.
And order management for receiving and processing orders.

## Features

- **Inventory Management:** Includes support for product categories, allowing for better organization and filtering of items. Full CRUD operations for items and categories.
- **Order Management:** Facilitates creating and managing orders with real-time stock control. When an order is placed, stock is automatically decremented. Stock is replenished if an order is cancelled (under certain conditions). Order lifecycle events are tracked.
- **User Accounts & Authentication:** Provides a system for user registration and login (admins and customers). Role-based access control is implemented to protect administrative functions and associate orders with customers.

## Run

Navigate into the `backend` folder to run the API
```bash
cd backend/
```

Start development API
```bash
uv run fastapi dev
```

## Database migrations

This project uses Aerich for database migrations

Create initial database migration
```bash
uv run aerich init-db
```

Create a new database migration
```bash
uv run aerich migrate --name <migration_name>
```

Upgrade the database to the latest version
```bash
uv run aerich upgrade
```

List all migrations
```bash
uv run aerich history
```


## Technology

- [uv](https://docs.astral.sh/uv/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [TortoiseORM](https://tortoise-orm.readthedocs.io/en/latest/)
- [Aerich](https://tortoise-orm.readthedocs.io/en/latest/aerich.html)
- [SQLite](https://www.sqlite.org/index.html)
- [Svix-KSUID](https://github.com/svix/python-ksuid)
- [python-jose](https://github.com/mpdavis/python-jose)
- [bcrypt](https://github.com/pyca/bcrypt/)
- [pytest](https://docs.pytest.org/en/stable/) (for testing)

## Logging Configuration

The application uses Python's standard `logging` module. Logging is configured in `src/app/main.py`.

### Namespaces

Loggers are named hierarchically based on their module path (e.g., `app.main`, `app.features.orders.router`, `app.features.inventory.service`). This allows for fine-grained control over log output.

The root logger for this application is named `app`.

### Setting Log Levels

You can control the verbosity of different parts of the application by setting log levels.

1.  **Default Application Log Level:**
    In `src/app/main.py`, the default level for the `app` logger is set:
    ```python
    app_logger = logging.getLogger("app")
    app_logger.setLevel(logging.INFO) # Default is INFO
    ```
    You can change `logging.INFO` to `logging.DEBUG`, `logging.WARNING`, etc.

2.  **Namespace-Specific Log Levels:**
    You can override the default level for specific namespaces. For example, to get more detailed logs from the `orders` feature, add or modify the following in `src/app/main.py`:
    ```python
    logging.getLogger("app.features.orders").setLevel(logging.DEBUG)
    ```
    This will show `DEBUG` messages from `app.features.orders` and its submodules (like `app.features.orders.router`), while other parts of the app might still be at `INFO`.

### Advanced Filtering with `NamespaceFilter`

For more precise control, a `NamespaceFilter` is available. This filter allows you to specify exactly which namespaces should produce log output, effectively silencing others.

To use it, uncomment and configure the following lines in `src/app/main.py`:

```python
# --- Namespace-based Filter (Optional) ---
# To only allow logs from specific top-level namespaces.
# For example, to only see logs from "app.features" and "app.main":
#
# allowed_log_namespaces = ["app.features.orders", "app.main"] # Example: only orders and main
# namespace_filter = NamespaceFilter(allowed_log_namespaces)
# console_handler.addFilter(namespace_filter)
```

-   Modify the `allowed_log_namespaces` list to include the namespaces you want to see.
-   If `allowed_log_namespaces` is empty or not set, the filter will allow all log messages that otherwise meet the level requirements.
