import logging
import pytest
from unittest.mock import MagicMock

# The NamespaceFilter class is kept as it is a core part of what's being tested.
class NamespaceFilter(logging.Filter):
    """
    A logging filter that allows log records from specified namespaces.
    """
    def __init__(self, allowed_namespaces=None):
        super().__init__()
        self.allowed_namespaces = allowed_namespaces if allowed_namespaces is not None else []

    def filter(self, record):
        if not self.allowed_namespaces:
            return True # Allow all records if no specific namespaces are listed
        # Check if the record's logger name starts with any of the allowed namespaces
        return any(record.name.startswith(ns) for ns in self.allowed_namespaces)

@pytest.fixture
def logging_env():
    """
    A pytest fixture to set up and tear down a controlled logging environment for tests.

    This fixture provides a mock handler and ensures that loggers are clean
    before and after each test, preventing interference between them.

    Yields:
        MagicMock: A mock logging handler to inspect calls and logged messages.
    """
    # --- Setup Phase (replaces unittest.setUp) ---
    test_handler = MagicMock()
    # Add required attributes for a handler
    test_handler.level = logging.NOTSET
    test_handler.filters = []
    test_handler.handleError = MagicMock()
    
    # Create proper side effects that modify the handler's state
    def add_filter(filter_obj):
        test_handler.filters.append(filter_obj)
        return filter_obj
        
    def remove_filter(filter_obj):
        if filter_obj in test_handler.filters:
            test_handler.filters.remove(filter_obj)
        return filter_obj
    
    # Define handle method that applies filters and tracks accepted records
    accepted_records = []
    def handle(record):
        # Apply all filters
        for f in test_handler.filters:
            if not f.filter(record):
                return False  # Skip this record if any filter rejects it
        
        # Record passed all filters, store it
        accepted_records.append(record)
        return True
        
    test_handler.addFilter = MagicMock(side_effect=add_filter)
    test_handler.removeFilter = MagicMock(side_effect=remove_filter)
    test_handler.handle = MagicMock(side_effect=handle)
    
    # Store accepted records for later assertion checks
    test_handler.accepted_records = accepted_records

    formatter = logging.Formatter('%(name)s:%(levelname)s:%(message)s')
    test_handler.setFormatter(formatter)

    # List of loggers to manage during tests
    loggers_to_manage = [
        "app", "app.features.orders", "app.features.inventory",
        "app.features.orders.submodule", "app.features.inventory.submodule", "app.main"
    ]

    # Clean up handlers and filters from previous tests
    for logger_name in loggers_to_manage:
        logger = logging.getLogger(logger_name)
        logger.handlers = []
        logger.filters = []
        logger.setLevel(logging.NOTSET)

    # Also clear the root logger's handlers
    logging.getLogger().handlers = []

    yield test_handler

    # --- Teardown Phase (replaces unittest.tearDown) ---
    # The setup phase already cleans up at the start of the next test,
    # but this ensures a clean state even after the last test runs.
    for logger_name in loggers_to_manage:
        logger = logging.getLogger(logger_name)
        logger.handlers = []
        logger.filters = []
        logger.setLevel(logging.NOTSET)
    logging.getLogger().handlers = []


def _setup_logger(name, level, handler_to_add):
    """Helper function to configure a logger for testing."""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.handlers = [handler_to_add]
    logger.propagate = True
    return logger

def get_handled_messages(test_handler: MagicMock) -> list[str]:
    """Extracts formatted log messages from the mock handler's accepted records."""
    messages = []
    for record in test_handler.accepted_records:
        messages.append(f"{record.name}:{record.levelname}:{record.getMessage()}")
    return messages

def test_default_level_propagation(logging_env):
    """
    Tests that child loggers correctly inherit the logging level from their parent.
    """
    # The root 'app' logger is set to INFO
    _setup_logger("app", logging.INFO, logging_env)

    # Child loggers should inherit the INFO level
    orders_logger = logging.getLogger("app.features.orders")
    inventory_logger = logging.getLogger("app.features.inventory")

    # Log messages at different levels
    orders_logger.debug("Order debug message")  # Should be ignored
    orders_logger.info("Order info message")   # Should be handled
    inventory_logger.info("Inventory info message") # Should be handled
    inventory_logger.warning("Inventory warning message") # Should be handled

    # Assertions
    handled_messages = get_handled_messages(logging_env)
    assert "app.features.orders:DEBUG:Order debug message" not in handled_messages
    assert "app.features.orders:INFO:Order info message" in handled_messages
    assert "app.features.inventory:INFO:Inventory info message" in handled_messages
    assert "app.features.inventory:WARNING:Inventory warning message" in handled_messages

def test_namespace_specific_level(logging_env):
    """
    Tests that a specific namespace can have its own logging level (e.g., DEBUG)
    that overrides the parent's level (e.g., INFO).
    """
    # Parent is INFO, but a specific feature is set to DEBUG
    _setup_logger("app", logging.INFO, logging_env)
    _setup_logger("app.features.orders", logging.DEBUG, logging_env)

    orders_logger = logging.getLogger("app.features.orders")
    inventory_logger = logging.getLogger("app.features.inventory")

    # Log messages
    orders_logger.debug("Order debug specific")  # Allowed by specific override
    orders_logger.info("Order info specific")
    inventory_logger.debug("Inventory debug specific") # Not allowed by parent's INFO level
    inventory_logger.info("Inventory info specific")

    # Assertions
    handled_messages = get_handled_messages(logging_env)
    assert "app.features.orders:DEBUG:Order debug specific" in handled_messages
    assert "app.features.orders:INFO:Order info specific" in handled_messages
    assert "app.features.inventory:DEBUG:Inventory debug specific" not in handled_messages
    assert "app.features.inventory:INFO:Inventory info specific" in handled_messages

def test_namespace_filter_allow(logging_env):
    """
    Tests that the NamespaceFilter correctly allows messages from a specified
    namespace while blocking others.
    """
    # Set the base logger to DEBUG to ensure the filter is responsible for blocking
    app_logger = _setup_logger("app", logging.DEBUG, logging_env)

    # Filter to only allow logs from the 'app.features.orders' namespace
    ns_filter = NamespaceFilter(allowed_namespaces=["app.features.orders"])
    logging_env.addFilter(ns_filter)

    # Log from various namespaces
    logging.getLogger("app.features.orders.submodule").info("Order message (allowed by filter)")
    logging.getLogger("app.features.inventory.submodule").info("Inventory message (should be filtered out)")
    logging.getLogger("app.main").info("Main app message (should be filtered out)")

    # Assertions
    handled_messages = get_handled_messages(logging_env)
    assert "app.features.orders.submodule:INFO:Order message (allowed by filter)" in handled_messages
    assert "app.features.inventory.submodule:INFO:Inventory message (should be filtered out)" not in handled_messages
    assert "app.main:INFO:Main app message (should be filtered out)" not in handled_messages

def test_namespace_filter_allow_all_if_empty(logging_env):
    """
    Tests that the NamespaceFilter allows all messages if the list of allowed
    namespaces is empty.
    """
    # Setup logger and an empty filter
    _setup_logger("app", logging.DEBUG, logging_env)
    ns_filter = NamespaceFilter(allowed_namespaces=[])  # Empty list should allow all
    logging_env.addFilter(ns_filter)

    # Log from different namespaces
    logging.getLogger("app.features.orders").info("Order message (filter empty)")
    logging.getLogger("app.features.inventory").info("Inventory message (filter empty)")

    # Assertions
    handled_messages = get_handled_messages(logging_env)
    assert "app.features.orders:INFO:Order message (filter empty)" in handled_messages
    assert "app.features.inventory:INFO:Inventory message (filter empty)" in handled_messages
