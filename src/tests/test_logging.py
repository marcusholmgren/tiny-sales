import logging
import unittest
from unittest.mock import MagicMock, patch

# Assuming src/app/main.py can be imported and it sets up the initial logging
# This might require PYTHONPATH adjustments depending on how tests are run.
# For simplicity, we'll re-apply some configuration parts here or mock them.
# Ideally, the app's logging setup would be callable or more easily testable.

# Import the filter from the app.main or define it again if direct import is tricky
# For this subtask, let's assume app.main can be imported or we redefine the filter.
# If src.app.main cannot be imported due to path issues, we might need to redefine NamespaceFilter
# For now, let's assume it's available via from app.main import NamespaceFilter,
# or it's simple enough to redefine for the test.

# Re-define NamespaceFilter if direct import from app.main is problematic in test environment
class NamespaceFilter(logging.Filter):
    def __init__(self, allowed_namespaces=None):
        super().__init__()
        self.allowed_namespaces = allowed_namespaces if allowed_namespaces is not None else []

    def filter(self, record):
        if not self.allowed_namespaces:
            return True
        return any(record.name.startswith(ns) for ns in self.allowed_namespaces)

class TestLoggingConfiguration(unittest.TestCase):

    def setUp(self):
        # Create a handler that we can inspect
        self.test_handler = MagicMock(spec=logging.Handler)
        self.test_handler.handleError = MagicMock() # Mock handleError to avoid issues if it's called

        # Basic formatter
        self.formatter = logging.Formatter('%(name)s:%(levelname)s:%(message)s')
        self.test_handler.setFormatter(self.formatter)

        # Clean up any existing handlers on root logger or specific loggers we test
        # and reset levels to avoid interference between tests.
        logging.getLogger().handlers = [] # Clear root handlers

        # Explicitly clear handlers and reset levels for loggers used in tests
        loggers_to_reset = ["app", "app.features.orders", "app.features.inventory", "app.features.orders.submodule", "app.features.inventory.submodule", "app.main"]
        for logger_name in loggers_to_reset:
            logger = logging.getLogger(logger_name)
            logger.handlers = []
            logger.setLevel(logging.NOTSET)
            # Ensure filters are also cleared if they could persist
            for f in logger.filters[:]:
                logger.removeFilter(f)

        # Clear filters from the test_handler itself as it might be reused implicitly by loggers
        for f in self.test_handler.filters[:]:
            self.test_handler.removeFilter(f)


    def tearDown(self):
        # Clean up handlers from loggers after each test
        loggers_to_reset = ["app", "app.features.orders", "app.features.inventory", "app.features.orders.submodule", "app.features.inventory.submodule", "app.main"]
        for logger_name in loggers_to_reset:
            logger = logging.getLogger(logger_name)
            logger.handlers = []
            logger.setLevel(logging.NOTSET)
            for f in logger.filters[:]:
                logger.removeFilter(f)

        logging.getLogger().handlers = [] # Clear root handlers again for safety

        # Clear filters from the test_handler
        for f in self.test_handler.filters[:]:
            self.test_handler.removeFilter(f)


    def _setup_logger(self, name, level, handler_to_add):
        logger = logging.getLogger(name)
        logger.setLevel(level)
        # Remove all existing handlers to ensure a clean state for the specific logger
        for h in logger.handlers[:]:
            logger.removeHandler(h)
        logger.addHandler(handler_to_add)
        # Critical: Ensure logger propagates messages. If false, handler on parent won't get them.
        logger.propagate = True
        return logger

    def test_default_level_propagation(self):
        # Setup root 'app' logger
        app_logger = self._setup_logger("app", logging.INFO, self.test_handler)

        # Child loggers - they should inherit the level from 'app'
        # and pass messages to 'app_logger's handler (self.test_handler)
        orders_logger = logging.getLogger("app.features.orders")
        inventory_logger = logging.getLogger("app.features.inventory")

        orders_logger.debug("Order debug message") # Should not pass INFO level of app_logger
        orders_logger.info("Order info message")
        inventory_logger.info("Inventory info message")
        inventory_logger.warning("Inventory warning message")

        handled_messages = []
        for call_arg in self.test_handler.handle.call_args_list:
            record = call_arg[0][0]
            handled_messages.append(f"{record.name}:{record.levelname}:{record.message}")

        self.assertNotIn("app.features.orders:DEBUG:Order debug message", handled_messages)
        self.assertIn("app.features.orders:INFO:Order info message", handled_messages)
        self.assertIn("app.features.inventory:INFO:Inventory info message", handled_messages)
        self.assertIn("app.features.inventory:WARNING:Inventory warning message", handled_messages)

    def test_namespace_specific_level(self):
        # app_logger is INFO, but app.features.orders is DEBUG
        self._setup_logger("app", logging.INFO, self.test_handler)
        orders_logger = self._setup_logger("app.features.orders", logging.DEBUG, self.test_handler)

        # inventory_logger will use 'app's logger settings (INFO)
        inventory_logger = logging.getLogger("app.features.inventory")
        # Ensure inventory_logger also sends to test_handler via propagation to app_logger

        orders_logger.debug("Order debug specific") # Allowed by orders_logger's DEBUG level
        orders_logger.info("Order info specific")
        inventory_logger.debug("Inventory debug specific") # Not allowed by app's INFO level
        inventory_logger.info("Inventory info specific") # Allowed by app's INFO level

        handled_messages = []
        for call_arg in self.test_handler.handle.call_args_list:
            record = call_arg[0][0]
            handled_messages.append(f"{record.name}:{record.levelname}:{record.message}")

        self.assertIn("app.features.orders:DEBUG:Order debug specific", handled_messages)
        self.assertIn("app.features.orders:INFO:Order info specific", handled_messages)
        self.assertNotIn("app.features.inventory:DEBUG:Inventory debug specific", handled_messages)
        self.assertIn("app.features.inventory:INFO:Inventory info specific", handled_messages)

    def test_namespace_filter_allow(self):
        # Set root logger to DEBUG to ensure filter is the one deciding, not level
        app_logger = self._setup_logger("app", logging.DEBUG, self.test_handler)

        ns_filter = NamespaceFilter(allowed_namespaces=["app.features.orders"])
        self.test_handler.addFilter(ns_filter) # Filter added to the handler

        # Loggers - will propagate to app_logger which has the filtered handler
        orders_logger = logging.getLogger("app.features.orders.submodule")
        inventory_logger = logging.getLogger("app.features.inventory.submodule")
        main_logger = logging.getLogger("app.main")

        # Ensure their levels are also DEBUG so they pass messages up
        orders_logger.setLevel(logging.DEBUG)
        inventory_logger.setLevel(logging.DEBUG)
        main_logger.setLevel(logging.DEBUG)


        orders_logger.info("Order message (allowed by filter)")
        inventory_logger.info("Inventory message (should be filtered out)")
        main_logger.info("Main app message (should be filtered out)")

        handled_messages = []
        for call_arg in self.test_handler.handle.call_args_list:
            record = call_arg[0][0]
            handled_messages.append(f"{record.name}:{record.levelname}:{record.message}")

        self.assertIn("app.features.orders.submodule:INFO:Order message (allowed by filter)", handled_messages)
        self.assertNotIn("app.features.inventory.submodule:INFO:Inventory message (should be filtered out)", handled_messages)
        self.assertNotIn("app.main:INFO:Main app message (should be filtered out)", handled_messages)

        self.test_handler.removeFilter(ns_filter) # Clean up filter


    def test_namespace_filter_allow_all_if_empty(self):
        app_logger = self._setup_logger("app", logging.DEBUG, self.test_handler)

        ns_filter = NamespaceFilter(allowed_namespaces=[]) # Empty list means allow all
        self.test_handler.addFilter(ns_filter)

        orders_logger = logging.getLogger("app.features.orders")
        inventory_logger = logging.getLogger("app.features.inventory")
        orders_logger.setLevel(logging.DEBUG)
        inventory_logger.setLevel(logging.DEBUG)

        orders_logger.info("Order message (filter empty)")
        inventory_logger.info("Inventory message (filter empty)")

        handled_messages = []
        for call_arg in self.test_handler.handle.call_args_list:
            record = call_arg[0][0]
            handled_messages.append(f"{record.name}:{record.levelname}:{record.message}")

        self.assertIn("app.features.orders:INFO:Order message (filter empty)", handled_messages)
        self.assertIn("app.features.inventory:INFO:Inventory message (filter empty)", handled_messages)

        self.test_handler.removeFilter(ns_filter)

if __name__ == '__main__':
    unittest.main()
