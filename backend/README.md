# Tiny sale API


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
