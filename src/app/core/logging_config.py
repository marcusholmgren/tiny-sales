import logging
import sys

class NamespaceFilter(logging.Filter):
    def __init__(self, allowed_namespaces=None):
        super().__init__()
        self.allowed_namespaces = allowed_namespaces if allowed_namespaces is not None else []

    def filter(self, record):
        if not self.allowed_namespaces:
            return True # If no namespaces are specified, allow all records
        # Allow record if its name starts with any of the allowed namespaces
        return any(record.name.startswith(ns) for ns in self.allowed_namespaces)

log_formatter = logging.Formatter(
    fmt="%(asctime)s - %(name)s:%(lineno)d - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

app_logger = logging.getLogger("app")
app_logger.setLevel(logging.INFO)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_formatter)

# --- Namespace-based Filter (Optional) ---
# To only allow logs from specific top-level namespaces.
# For example, to only see logs from "app.features" and "app.main":
#
# allowed_log_namespaces = ["app.features", "app.main"]
# namespace_filter = NamespaceFilter(allowed_log_namespaces)
# console_handler.addFilter(namespace_filter)
#
# If `allowed_log_namespaces` is empty or None, the filter will allow all logs.
# This can be driven by environment variables for more dynamic control.
# For now, it's commented out to not break existing logging behavior
# until explicitly configured by the user.
app_logger.addHandler(console_handler)

# --- Namespace-specific logging level configuration examples ---
# To set a different level for a specific part of the application:
# For example, to see DEBUG messages from the 'orders' feature:
logging.getLogger("app.features.orders").setLevel(logging.DEBUG)

# And perhaps less verbose logging for another part:
# logging.getLogger("app.features.inventory").setLevel(logging.WARNING)

# Note: For these configurations to take effect, modules must use
# logging.getLogger(__name__) which will create loggers like
# "app.features.orders.router" or "app.services.some_service".
# These child loggers will inherit levels from their parents (e.g., "app.features.orders")
# or the application's root logger ("app") if not specifically set.



# sh = logging.StreamHandler(sys.stdout)
# sh.setLevel(logging.DEBUG)
# sh.setFormatter(fmt)
# # will print debug sql
# logger_db_client = logging.getLogger("tortoise.db_client")
# logger_db_client.setLevel(logging.DEBUG)
# # logger_db_client.addHandler(sh)
#
# logger_tortoise = logging.getLogger("tortoise")
# logger_tortoise.setLevel(logging.DEBUG)
# # logger_tortoise.addHandler(sh)
