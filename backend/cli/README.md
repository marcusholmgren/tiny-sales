# Tiny Sales CLI

This command-line interface (CLI) provides tools for managing the Tiny Sales application data, primarily focused on user administration and database interactions.

## Prerequisites

- Python 3.x installed.
- Required dependencies installed (as per the project's `pyproject.toml` or `requirements.txt`).
- The application's database should be configured and accessible. The CLI uses the `DATABASE_URL` environment variable or defaults to `sqlite://./tiny_sales.sqlite3` relative to the project root.

## Running the CLI

The main CLI script is `main.py` located in the `backend/cli/` directory.

You can run the CLI commands from the project's root directory (`tiny-sales/`) or from the `backend/` directory.

**From the project root (`tiny-sales/`):**
```bash
python backend/cli/main.py [COMMANDS]
```

**From the `backend/` directory:**
```bash
python cli/main.py [COMMANDS]
```

To see the help message and list of all available commands:
```bash
python backend/cli/main.py --help
```

## Available Commands

The CLI is organized into sub-commands.

### User Management (`users`)

These commands are available under the `users` subcommand. To see help for user management:
```bash
python backend/cli/main.py users --help
```

#### `users create-admin`

Creates a new administrative user. You will be prompted to enter the username, email, and password for the new admin.

**Usage:**
```bash
python backend/cli/main.py users create-admin
```
**Options (will be prompted if not provided):**
  * `--username TEXT`: Username for the new admin. (Required)
  * `--email TEXT`: Email for the new admin. (Required)
  * `--password TEXT`: Password for the new admin. (Required)

#### `users promote-to-admin`

Promotes an existing user to the admin role.

**Usage:**
```bash
python backend/cli/main.py users promote-to-admin <USERNAME>
```
**Arguments:**
  * `USERNAME`: The username of the user to promote. (Required)

#### `users disable-user`

Disables an existing user's account, preventing them from logging in.

**Usage:**
```bash
python backend/cli/main.py users disable-user <USERNAME>
```
**Arguments:**
  * `USERNAME`: The username of the user to disable. (Required)

#### `users enable-user`

Enables a previously disabled user's account.

**Usage:**
```bash
python backend/cli/main.py users enable-user <USERNAME>
```
**Arguments:**
  * `USERNAME`: The username of the user to enable. (Required)

### Database (`test-db-connection`)

#### `test-db-connection`

Tests the database connection configured for the application and lists the number of users found. This is useful for verifying that the CLI can connect to and interact with the database.

**Usage:**
```bash
python backend/cli/main.py test-db-connection
```

## Environment Variables

- `DATABASE_URL`: Specifies the database connection string. If not set, defaults to `sqlite://./tiny_sales.sqlite3` (relative to the project root).
- `SECRET_KEY`: Used for JWT token generation in the broader application, though not directly by all CLI commands.
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Defines the expiry time for access tokens.

## Troubleshooting

- **`ModuleNotFoundError`**: Ensure you are running the commands from the correct directory (project root or `backend/`) and that `sys.path` is correctly configured in `cli/main.py` to find the `backend` package.
- **Database Connection Issues**: Verify that your `DATABASE_URL` is correct and the database server is running and accessible. The `test-db-connection` command can help diagnose this.
- **Asyncio RuntimeWarnings**: Some commands are asynchronous. If you see `RuntimeWarning: coroutine ... was never awaited`, it might indicate an issue with how Typer is invoking an async command. The `test-db-connection` command has been wrapped to handle this; other async commands might need similar treatment if issues arise.

