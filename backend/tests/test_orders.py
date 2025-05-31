import pytest
from fastapi.testclient import TestClient

# Assuming models and schemas might be needed for direct assertions or setup
from backend.models import Order, OrderItem, OrderEvent, InventoryItem, generate_ksuid
from backend.schemas import OrderPublicSchema # Assuming this exists or will be created
# from backend.schemas import OrderItemPublicSchema, OrderShipRequestSchema, OrderCancelRequestSchema # Ensure these exist if used

# Use anyio_backend fixture from conftest if not already picked up
pytestmark = pytest.mark.anyio


async def setup_test_inventory_item():
    # Helper to create a sample inventory item for tests
    # Ensure this doesn't conflict with DB state if tests run in parallel or share DB
    # For function-scoped client, this should be fine if DB is reset or transactions are used.
    item = await InventoryItem.create(name="Test Product 1", quantity=100)
    return item

async def test_create_order_success(client: TestClient): # Changed from TestClient
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
    response = client.post("/api/v1/orders/", json=order_payload)
    assert response.status_code == 201, response.text
    data = response.json()

    assert data["public_id"] is not None
    assert data["order_id"] is not None # e.g., "20240001" or similar
    assert data["contact_name"] == "Test User"
    # Assuming initial status is 'placed' or similar, adjust if your logic differs
    assert data["status"] == "placed" # Or whatever the initial status is
    assert len(data["items"]) == 1
    assert data["items"][0]["product_public_id"] == inventory_item.public_id
    assert data["items"][0]["quantity"] == 2
    assert data["items"][0]["price_at_purchase"] == 10.50

    # Assuming events are part of the response schema
    assert len(data["events"]) >= 1 # At least 'order_placed'
    assert data["events"][0]["event_type"] == "order_placed"

    from datetime import datetime
    current_year = str(datetime.now().year)
    assert data["order_id"].startswith(current_year)

async def create_order_for_test(client: TestClient, inventory_item_public_id: str, contact_name: str = "Test Order User") -> OrderPublicSchema:
    """Helper function to create an order for testing purposes."""
    order_payload = {
        "contact_name": contact_name,
        "contact_email": "testorder@example.com",
        "delivery_address": "123 Test Order St",
        "items": [
            {
                "product_public_id": inventory_item_public_id,
                "quantity": 1,
                "price_at_purchase": 25.00
            }
        ]
    }
    response = client.post("/api/v1/orders/", json=order_payload)
    assert response.status_code == 201, response.text
    # Assuming OrderPublicSchema is defined and matches the response structure
    return OrderPublicSchema(**response.json())


async def test_create_order_no_items(client: TestClient):
    order_payload = {
        "contact_name": "Test User No Items",
        "contact_email": "testnoitems@example.com",
        "delivery_address": "456 NoItem Rd",
        "items": [] # Empty items list
    }
    response = client.post("/api/v1/orders/", json=order_payload)
    assert response.status_code == 422 # FastAPI's validation error for Pydantic min_items=1 (or similar)

async def test_get_order_success(client: TestClient):
    inventory_item = await setup_test_inventory_item()
    # Use the helper to create an order
    created_order = await create_order_for_test(client, inventory_item.public_id, "Get Order Test User")
    order_public_id = created_order.public_id

    get_response = client.get(f"/api/v1/orders/{order_public_id}")
    assert get_response.status_code == 200, get_response.text
    retrieved_order_data = get_response.json()

    assert retrieved_order_data["public_id"] == order_public_id
    assert retrieved_order_data["contact_name"] == "Get Order Test User"
    assert len(retrieved_order_data["items"]) == 1
    assert retrieved_order_data["items"][0]["product_public_id"] == inventory_item.public_id
    assert len(retrieved_order_data["events"]) > 0

async def test_get_order_not_found(client: TestClient):
    non_existent_ksuid = generate_ksuid()
    response = client.get(f"/api/v1/orders/{non_existent_ksuid}")
    assert response.status_code == 404

# --- Tests for PATCH /orders/{order_public_id}/ship ---

async def test_ship_order_success_no_details(client: TestClient):
    inventory_item = await setup_test_inventory_item()
    order = await create_order_for_test(client, inventory_item.public_id, "Ship Order No Details User")

    response = client.patch(f"/api/v1/orders/{order.public_id}/ship")
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["public_id"] == order.public_id
    assert data["status"] == "shipped"

    updated_order = await Order.get(public_id=order.public_id).prefetch_related("events")
    assert updated_order.status == "shipped"
    shipped_event = next((e for e in updated_order.events if e.event_type == "order_shipped"), None)
    assert shipped_event is not None
    assert shipped_event.data == {"message": "Order marked as shipped."} # Or similar default

async def test_ship_order_success_with_details(client: TestClient):
    inventory_item = await setup_test_inventory_item()
    order = await create_order_for_test(client, inventory_item.public_id, "Ship Order With Details User")

    ship_payload = {
        "tracking_number": "TRK12345",
        "shipping_provider": "FastShip"
    }
    response = client.patch(f"/api/v1/orders/{order.public_id}/ship", json=ship_payload)
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["status"] == "shipped"
    assert data["public_id"] == order.public_id

    updated_order_db = await Order.get(public_id=order.public_id).prefetch_related("events")
    assert updated_order_db.status == "shipped"
    shipped_event = next((e for e in updated_order_db.events if e.event_type == "order_shipped"), None)
    assert shipped_event is not None
    assert shipped_event.data["tracking_number"] == "TRK12345"
    assert shipped_event.data["shipping_provider"] == "FastShip"

async def test_ship_order_not_found(client: TestClient):
    non_existent_ksuid = generate_ksuid()
    response = client.patch(f"/api/v1/orders/{non_existent_ksuid}/ship")
    assert response.status_code == 404

async def test_ship_order_already_shipped(client: TestClient):
    inventory_item = await setup_test_inventory_item()
    order = await create_order_for_test(client, inventory_item.public_id, "Already Shipped User")

    client.patch(f"/api/v1/orders/{order.public_id}/ship") # Ship it once
    response = client.patch(f"/api/v1/orders/{order.public_id}/ship") # Try to ship again
    assert response.status_code == 400
    assert "already shipped" in response.json()["detail"].lower()

async def test_ship_order_cancelled(client: TestClient):
    inventory_item = await setup_test_inventory_item()
    order = await create_order_for_test(client, inventory_item.public_id, "Ship Cancelled User")

    client.patch(f"/api/v1/orders/{order.public_id}/cancel", json={"reason": "Test cancellation"}) # Cancel it
    response = client.patch(f"/api/v1/orders/{order.public_id}/ship") # Try to ship
    assert response.status_code == 400
    assert "cannot ship a cancelled order" in response.json()["detail"].lower()

# --- Tests for PATCH /orders/{order_public_id}/cancel ---

async def test_cancel_order_success_no_reason(client: TestClient):
    inventory_item = await setup_test_inventory_item()
    order = await create_order_for_test(client, inventory_item.public_id, "Cancel No Reason User")

    response = client.patch(f"/api/v1/orders/{order.public_id}/cancel")
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["public_id"] == order.public_id
    assert data["status"] == "cancelled"

    updated_order = await Order.get(public_id=order.public_id).prefetch_related("events")
    assert updated_order.status == "cancelled"
    cancelled_event = next((e for e in updated_order.events if e.event_type == "order_cancelled"), None)
    assert cancelled_event is not None
    assert cancelled_event.data == {"message": "Order marked as cancelled."} # Or similar

async def test_cancel_order_success_with_reason(client: TestClient):
    inventory_item = await setup_test_inventory_item()
    order = await create_order_for_test(client, inventory_item.public_id, "Cancel With Reason User")

    cancel_payload = {"reason": "Customer changed mind"}
    response = client.patch(f"/api/v1/orders/{order.public_id}/cancel", json=cancel_payload)
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["status"] == "cancelled"
    assert data["public_id"] == order.public_id

    updated_order_db = await Order.get(public_id=order.public_id).prefetch_related("events")
    assert updated_order_db.status == "cancelled"
    cancelled_event = next((e for e in updated_order_db.events if e.event_type == "order_cancelled"), None)
    assert cancelled_event is not None
    assert cancelled_event.data["reason"] == "Customer changed mind"

async def test_cancel_order_not_found(client: TestClient):
    non_existent_ksuid = generate_ksuid()
    response = client.patch(f"/api/v1/orders/{non_existent_ksuid}/cancel")
    assert response.status_code == 404

async def test_cancel_order_already_cancelled(client: TestClient):
    inventory_item = await setup_test_inventory_item()
    order = await create_order_for_test(client, inventory_item.public_id, "Already Cancelled User")

    client.patch(f"/api/v1/orders/{order.public_id}/cancel") # Cancel it once
    response = client.patch(f"/api/v1/orders/{order.public_id}/cancel") # Try to cancel again
    assert response.status_code == 400
    assert "already cancelled" in response.json()["detail"].lower()

async def test_cancel_order_shipped_allowed_with_reason(client: TestClient):
    inventory_item = await setup_test_inventory_item()
    order = await create_order_for_test(client, inventory_item.public_id, "Cancel Shipped User")

    client.patch(f"/api/v1/orders/{order.public_id}/ship", json={"tracking_number": "TRKSHIPFIRST"})
    cancel_payload = {"reason": "Customer requested cancellation after shipping"}
    response = client.patch(f"/api/v1/orders/{order.public_id}/cancel", json=cancel_payload)
    assert response.status_code == 200, response.text # Assuming router allows this
    data = response.json()
    assert data["status"] == "cancelled"

    updated_order_db = await Order.get(public_id=order.public_id).prefetch_related("events")
    assert updated_order_db.status == "cancelled"
    cancelled_event = next((e for e in updated_order_db.events if e.event_type == "order_cancelled"), None)
    assert cancelled_event is not None
    assert cancelled_event.data["reason"] == "Customer requested cancellation after shipping"

async def test_cancel_order_shipped_allowed_no_reason(client: TestClient):
    inventory_item = await setup_test_inventory_item()
    order = await create_order_for_test(client, inventory_item.public_id, "Cancel Shipped No Reason User")

    client.patch(f"/api/v1/orders/{order.public_id}/ship", json={"tracking_number": "TRKSHIPFIRSTNOREASON"})
    response = client.patch(f"/api/v1/orders/{order.public_id}/cancel")
    assert response.status_code == 400, response.text # Assuming router allows this
    data = response.json()
    assert data["detail"] == "Cannot cancel a shipped order without a valid reason."

    updated_order_db = await Order.get(public_id=order.public_id).prefetch_related("events")
    assert updated_order_db.status == "shipped"
    cancelled_event = next((e for e in updated_order_db.events if e.event_type == "order_cancelled"), None)
    assert cancelled_event is None

# To run these tests:
# Ensure pytest, pytest-asyncio, and httpx are installed.
# From the project root (parent of 'backend'), run:
# PYTHONPATH=. pytest backend/tests/test_orders.py
# (or simply `pytest` if your project structure and pytest.ini/pyproject.toml are set up for discovery)
