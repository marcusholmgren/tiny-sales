import pytest
from fastapi.testclient import TestClient

# Assuming models and schemas might be needed for direct assertions or setup
from ..models import Order, OrderItem, OrderEvent, InventoryItem, generate_ksuid
from ..schemas import OrderPublicSchema # Assuming this exists or will be created
# from backend.schemas import OrderItemPublicSchema, OrderShipRequestSchema, OrderCancelRequestSchema # Ensure these exist if used

# Use anyio_backend fixture from conftest if not already picked up
pytestmark = pytest.mark.anyio


async def setup_test_inventory_item():
    # Helper to create a sample inventory item for tests
    # Ensure this doesn't conflict with DB state if tests run in parallel or share DB
    # For function-scoped client, this should be fine if DB is reset or transactions are used.
    item = await InventoryItem.create(name="Test Product 1", quantity=100)
    return item

async def get_auth_token(client: TestClient, username: str = "testuser", password: str = "testpassword123", email: str = "testuser@example.com") -> str:
    # Get token
    response = client.post("/api/v1/auth/token", data={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]

async def test_create_order_success(client: TestClient): # Changed from TestClient
    # Setup: Ensure an inventory item exists
    inventory_item = await setup_test_inventory_item()
    token = await get_auth_token(client)

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
    response = client.post(
        "/api/v1/orders/",
        json=order_payload,
        headers={"Authorization": f"Bearer {token}"}
    )
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
    token = await get_auth_token(client)
    response = client.post("/api/v1/orders/", json=order_payload,
                           headers={"Authorization": f"Bearer {token}"})
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
    token = await get_auth_token(client)
    response = client.post("/api/v1/orders/", json=order_payload,
                           headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 422 # FastAPI's validation error for Pydantic min_items=1 (or similar)

async def test_get_order_success(client: TestClient):
    inventory_item = await setup_test_inventory_item()
    # Use the helper to create an order
    created_order = await create_order_for_test(client, inventory_item.public_id, "Get Order Test User")
    order_public_id = created_order.public_id
    token = await get_auth_token(client)

    get_response = client.get(f"/api/v1/orders/{order_public_id}",
                              headers={"Authorization": f"Bearer {token}"})
    assert get_response.status_code == 200, get_response.text
    retrieved_order_data = get_response.json()

    assert retrieved_order_data["public_id"] == order_public_id
    assert retrieved_order_data["contact_name"] == "Get Order Test User"
    assert len(retrieved_order_data["items"]) == 1
    assert retrieved_order_data["items"][0]["product_public_id"] == inventory_item.public_id
    assert len(retrieved_order_data["events"]) > 0

async def test_get_order_not_found(client: TestClient):
    non_existent_ksuid = generate_ksuid()
    token = await get_auth_token(client)
    response = client.get(f"/api/v1/orders/{non_existent_ksuid}",
                          headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 404

# --- Tests for PATCH /orders/{order_public_id}/ship ---

async def test_ship_order_success_no_details(admin_client: TestClient): # Changed client to admin_client
    inventory_item = await setup_test_inventory_item()
    # Order creation can still use the regular client's token via create_order_for_test,
    # or be created by admin if create_order_for_test is adapted or admin token passed.
    # For now, assuming order creation by testuser is fine, focus is on PATCH auth.
    order = await create_order_for_test(admin_client, inventory_item.public_id, "Ship Order No Details User")
    # Token no longer needed from get_auth_token for the PATCH call

    response = admin_client.patch(f"/api/v1/orders/{order.public_id}/ship") # Removed headers
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["public_id"] == order.public_id
    assert data["status"] == "shipped"

    # DB verification remains important
    updated_order = await Order.get(public_id=order.public_id).prefetch_related("events")
    assert updated_order.status == "shipped"
    shipped_event = next((e for e in updated_order.events if e.event_type == "order_shipped"), None)
    assert shipped_event is not None
    assert shipped_event.data == {"message": "Order marked as shipped."} # Or similar default

async def test_ship_order_success_with_details(admin_client: TestClient): # Changed client to admin_client
    inventory_item = await setup_test_inventory_item()
    order = await create_order_for_test(admin_client, inventory_item.public_id, "Ship Order With Details User")
    # Token no longer needed from get_auth_token for the PATCH call

    ship_payload = {
        "tracking_number": "TRK12345",
        "shipping_provider": "FastShip"
    }
    response = admin_client.patch(f"/api/v1/orders/{order.public_id}/ship", json=ship_payload) # Removed headers
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

async def test_ship_order_not_found(admin_client: TestClient): # Changed client to admin_client
    non_existent_ksuid = generate_ksuid()
    # Token no longer needed from get_auth_token for the PATCH call
    response = admin_client.patch(f"/api/v1/orders/{non_existent_ksuid}/ship") # Removed headers
    assert response.status_code == 404

async def test_ship_order_already_shipped(admin_client: TestClient): # Changed client to admin_client
    inventory_item = await setup_test_inventory_item()
    order = await create_order_for_test(admin_client, inventory_item.public_id, "Already Shipped User")
    # Token no longer needed from get_auth_token for the PATCH call

    admin_client.patch(f"/api/v1/orders/{order.public_id}/ship") # Ship it once, using admin_client default headers
    response = admin_client.patch(f"/api/v1/orders/{order.public_id}/ship") # Try to ship again, using admin_client default headers
    assert response.status_code == 400
    assert "already shipped" in response.json()["detail"].lower()

async def test_ship_order_cancelled(admin_client: TestClient): # Changed client to admin_client
    inventory_item = await setup_test_inventory_item()
    order = await create_order_for_test(admin_client, inventory_item.public_id, "Ship Cancelled User")
    # Token no longer needed from get_auth_token for the PATCH calls

    # For cancelling, if it's an admin action, this should also use admin_client.
    # If cancelling can be done by users, then create_order_for_test might need adjustment or use regular client.
    # Assuming for this test, the sequence uses admin privileges for both cancel and ship attempt.
    admin_client.patch(f"/api/v1/orders/{order.public_id}/cancel", json={"reason": "Test cancellation"}) # Cancel it
    response = admin_client.patch(f"/api/v1/orders/{order.public_id}/ship") # Try to ship
    assert response.status_code == 400
    assert "cannot ship a cancelled order" in response.json()["detail"].lower()

# --- Tests for PATCH /orders/{order_public_id}/cancel ---

async def test_cancel_order_success_no_reason(admin_client: TestClient): # Changed client to admin_client
    inventory_item = await setup_test_inventory_item()
    order = await create_order_for_test(admin_client, inventory_item.public_id, "Cancel No Reason User")
    # Token no longer needed from get_auth_token

    response = admin_client.patch(f"/api/v1/orders/{order.public_id}/cancel") # Removed headers
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["public_id"] == order.public_id
    assert data["status"] == "cancelled"

    updated_order = await Order.get(public_id=order.public_id).prefetch_related("events")
    assert updated_order.status == "cancelled"
    cancelled_event = next((e for e in updated_order.events if e.event_type == "order_cancelled"), None)
    assert cancelled_event is not None
    assert cancelled_event.data == {"stock_replenished": True} # Updated expected event data

async def test_cancel_order_success_with_reason(admin_client: TestClient): # Changed client to admin_client
    inventory_item = await setup_test_inventory_item()
    order = await create_order_for_test(admin_client, inventory_item.public_id, "Cancel With Reason User")
    # Token no longer needed from get_auth_token

    cancel_payload = {"reason": "Customer changed mind"}
    response = admin_client.patch(f"/api/v1/orders/{order.public_id}/cancel", json=cancel_payload) # Removed headers
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["status"] == "cancelled"
    assert data["public_id"] == order.public_id

    updated_order_db = await Order.get(public_id=order.public_id).prefetch_related("events")
    assert updated_order_db.status == "cancelled"
    cancelled_event = next((e for e in updated_order_db.events if e.event_type == "order_cancelled"), None)
    assert cancelled_event is not None
    assert cancelled_event.data["reason"] == "Customer changed mind"

async def test_cancel_order_not_found(admin_client: TestClient): # Changed client to admin_client
    non_existent_ksuid = generate_ksuid()
    # Token no longer needed from get_auth_token
    response = admin_client.patch(f"/api/v1/orders/{non_existent_ksuid}/cancel") # Removed headers
    assert response.status_code == 404

async def test_cancel_order_already_cancelled(admin_client: TestClient): # Changed client to admin_client
    inventory_item = await setup_test_inventory_item()
    order = await create_order_for_test(admin_client, inventory_item.public_id, "Already Cancelled User")
    # Token no longer needed from get_auth_token

    admin_client.patch(f"/api/v1/orders/{order.public_id}/cancel") # Cancel it once
    response = admin_client.patch(f"/api/v1/orders/{order.public_id}/cancel") # Try to cancel again
    assert response.status_code == 400
    assert "already cancelled" in response.json()["detail"].lower()

async def test_cancel_order_shipped_allowed_with_reason(admin_client: TestClient): # Changed client to admin_client
    inventory_item = await setup_test_inventory_item()
    order = await create_order_for_test(admin_client, inventory_item.public_id, "Cancel Shipped User")
    # Token no longer needed from get_auth_token

    # Assuming shipping can be done by admin, then cancelling by admin.
    admin_client.patch(f"/api/v1/orders/{order.public_id}/ship", json={"tracking_number": "TRKSHIPFIRST"}) # Ship it first
    cancel_payload = {"reason": "Customer requested cancellation after shipping"}
    response = admin_client.patch(f"/api/v1/orders/{order.public_id}/cancel", json=cancel_payload) # Removed headers
    assert response.status_code == 200, response.text # Assuming router allows this
    data = response.json()
    assert data["status"] == "cancelled"

    updated_order_db = await Order.get(public_id=order.public_id).prefetch_related("events")
    assert updated_order_db.status == "cancelled"
    cancelled_event = next((e for e in updated_order_db.events if e.event_type == "order_cancelled"), None)
    assert cancelled_event is not None
    assert cancelled_event.data["reason"] == "Customer requested cancellation after shipping"

async def test_cancel_order_shipped_allowed_no_reason(admin_client: TestClient): # Changed client to admin_client
    inventory_item = await setup_test_inventory_item()
    order = await create_order_for_test(admin_client, inventory_item.public_id, "Cancel Shipped No Reason User")
    # Token no longer needed from get_auth_token

    admin_client.patch(f"/api/v1/orders/{order.public_id}/ship", json={"tracking_number": "TRKSHIPFIRSTNOREASON"}) # Ship it first
    response = admin_client.patch(f"/api/v1/orders/{order.public_id}/cancel") # Try to cancel without reason, removed headers
    assert response.status_code == 400, response.text # Assuming router validation as per original test
    data = response.json()
    assert data["detail"] == "Shipped order cancellation requires a reason for admin." # Updated expected message

    updated_order_db = await Order.get(public_id=order.public_id).prefetch_related("events")
    assert updated_order_db.status == "shipped" # Order should remain shipped
    cancelled_event = next((e for e in updated_order_db.events if e.event_type == "order_cancelled"), None)
    assert cancelled_event is None # No cancellation event should be created

# To run these tests:
# Ensure pytest, pytest-asyncio, and httpx are installed.
# From the project root (parent of 'backend'), run:
# PYTHONPATH=. pytest backend/tests/test_orders.py
# (or simply `pytest` if your project structure and pytest.ini/pyproject.toml are set up for discovery)
