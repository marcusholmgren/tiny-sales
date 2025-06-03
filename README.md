# Tiny sales

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
