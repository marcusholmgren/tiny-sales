import pytest
import sys
from pathlib import Path

# Import main fixtures from the project's top-level conftest.py
# First, get the path to the main conftest.py
project_root = Path(__file__).resolve().parents[4]  # Go up from tests -> orders -> features -> app -> src
src_tests_path = project_root / "tests"
sys.path.insert(0, str(src_tests_path))

# Import fixtures from main conftest.py
from conftest import (
    anyio_backend,
    app_for_testing,
    client,
    admin_client,
    test_user_admin_token,
    clean_db_each_test,
    test_user_customer_token
)

# You can add additional fixtures specific to orders tests here if needed