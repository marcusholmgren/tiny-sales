import pytest
from fastapi.testclient import TestClient
from backend.main import app # Or import client fixture from conftest

# Assuming models and schemas might be needed for direct assertions or setup
from backend.models import Order, OrderItem, OrderEvent, InventoryItem
from backend.schemas import OrderPublicSchema, OrderItemPublicSchema

# Use anyio_backend fixture from conftest if not already picked up
pytestmark = pytest.mark.anyio


async def setup_test_inventory_item(db_conn=None):
    # Helper to create a sample inventory item for tests
    item = await InventoryItem.create(name="Test Product 1", quantity=100)
    return item

async def test_create_order_success(client: TestClient):
    # Setup: Ensure an inventory item exists
    inventory_item = await setup_test_inventory_item()

    order_payload = {
        "contact_name": "Test User",
        "contact_email": "test@example.com",
        "delivery_address": "123 Test St, Testville",
        "items": [
            {
                "product_public_id": inventory_item.public_id,
                "quantity": 2,
                "price_at_purchase": 10.50
            }
        ]
    }
    response = await client.post("/api/v1/orders/", json=order_payload)
    assert response.status_code == 201
    data = response.json()

    assert data["public_id"] is not None
    assert data["order_id"] is not None # e.g., "20240001" or similar
    assert data["contact_name"] == "Test User"
    assert data["status"] == "placed"
    assert len(data["items"]) == 1
    assert data["items"][0]["product_public_id"] == inventory_item.public_id
    assert data["items"][0]["quantity"] == 2
    assert data["items"][0]["price_at_purchase"] == 10.50

    assert len(data["events"]) == 1
    assert data["events"][0]["event_type"] == "order_placed"

    # Verify internal order ID format (simple check for year prefix)
    # This might need adjustment based on how robust the year check should be
    from datetime import datetime
    current_year = str(datetime.now().year)
    assert data["order_id"].startswith(current_year)

async def test_create_order_no_items(client: TestClient):
    order_payload = {
        "contact_name": "Test User No Items",
        "contact_email": "testnoitems@example.com",
        "delivery_address": "456 NoItem Rd",
        "items": [] # Empty items list
    }
    response = await client.post("/api/v1/orders/", json=order_payload)
    assert response.status_code == 422 # FastAPI's validation error for Pydantic min_length

async def test_get_order_success(client: TestClient):
    # 1. Create an order first
    inventory_item = await setup_test_inventory_item()
    order_payload = {
        "contact_name": "Get Order Test",
        "contact_email": "get@example.com",
        "delivery_address": "789 Get St",
        "items": [{"product_public_id": inventory_item.public_id, "quantity": 1, "price_at_purchase": 20.00}]
    }
    create_response = await client.post("/api/v1/orders/", json=order_payload)
    assert create_response.status_code == 201
    created_order_data = create_response.json()
    order_public_id = created_order_data["public_id"]

    # 2. Retrieve the order
    get_response = await client.get(f"/api/v1/orders/{order_public_id}")
    assert get_response.status_code == 200
    retrieved_order_data = get_response.json()

    assert retrieved_order_data["public_id"] == order_public_id
    assert retrieved_order_data["contact_name"] == "Get Order Test"
    assert len(retrieved_order_data["items"]) == 1
    assert retrieved_order_data["items"][0]["product_public_id"] == inventory_item.public_id
    assert len(retrieved_order_data["events"]) > 0 # Should have at least 'order_placed'

async def test_get_order_not_found(client: TestClient):
    non_existent_ksuid = "000000000000000000000000000" # A valid KSUID format but likely non-existent
    response = await client.get(f"/api/v1/orders/{non_existent_ksuid}")
    assert response.status_code == 404

# To run these tests:
# Ensure pytest and pytest-asyncio are installed.
# From the project root (parent of 'backend'), run:
# PYTHONPATH=. pytest backend/tests
