import pytest
from httpx import AsyncClient # Use AsyncClient for async tests
from backend.main import app # Or import client fixture from conftest

# Assuming models and schemas might be needed for direct assertions or setup
from backend.models import Order, OrderItem, OrderEvent, InventoryItem, generate_ksuid
from backend.schemas import OrderPublicSchema, OrderItemPublicSchema, OrderShipRequestSchema, OrderCancelRequestSchema

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

async def create_order_for_test(client: AsyncClient, inventory_item_public_id: str, contact_name: str = "Test Order User") -> OrderPublicSchema:
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
    response = await client.post("/api/v1/orders/", json=order_payload)
    assert response.status_code == 201
    return OrderPublicSchema(**response.json())


async def test_create_order_no_items(client: AsyncClient):
    order_payload = {
        "contact_name": "Test User No Items",
        "contact_email": "testnoitems@example.com",
        "delivery_address": "456 NoItem Rd",
        "items": [] # Empty items list
    }
    response = await client.post("/api/v1/orders/", json=order_payload)
    assert response.status_code == 422 # FastAPI's validation error for Pydantic min_length

async def test_get_order_success(client: AsyncClient):
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

async def test_get_order_not_found(client: AsyncClient):
    non_existent_ksuid = generate_ksuid() # Generate a valid KSUID that won't exist
    response = await client.get(f"/api/v1/orders/{non_existent_ksuid}")
    assert response.status_code == 404

# --- Tests for PATCH /orders/{order_public_id}/ship ---

async def test_ship_order_success_no_details(client: AsyncClient):
    inventory_item = await setup_test_inventory_item()
    order = await create_order_for_test(client, inventory_item.public_id, "Ship Order No Details User")

    response = await client.patch(f"/api/v1/orders/{order.public_id}/ship")
    assert response.status_code == 200
    data = response.json()

    assert data["public_id"] == order.public_id
    assert data["status"] == "shipped"

    # Verify OrderEvent
    updated_order = await Order.get(public_id=order.public_id).prefetch_related("events")
    assert updated_order.status == "shipped"
    shipped_event = next((e for e in updated_order.events if e.event_type == "order_shipped"), None)
    assert shipped_event is not None
    assert shipped_event.data == {"message": "Order marked as shipped."}

async def test_ship_order_success_with_details(client: AsyncClient):
    inventory_item = await setup_test_inventory_item()
    order = await create_order_for_test(client, inventory_item.public_id, "Ship Order With Details User")

    ship_payload = {
        "tracking_number": "TRK12345",
        "shipping_provider": "FastShip"
    }
    response = await client.patch(f"/api/v1/orders/{order.public_id}/ship", json=ship_payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "shipped"
    assert data["public_id"] == order.public_id

    # Verify OrderEvent directly from DB to be sure
    updated_order_db = await Order.get(public_id=order.public_id).prefetch_related("events")
    assert updated_order_db.status == "shipped"
    shipped_event = next((e for e in updated_order_db.events if e.event_type == "order_shipped"), None)
    assert shipped_event is not None
    assert shipped_event.data["tracking_number"] == "TRK12345"
    assert shipped_event.data["shipping_provider"] == "FastShip"

async def test_ship_order_not_found(client: AsyncClient):
    non_existent_ksuid = generate_ksuid()
    response = await client.patch(f"/api/v1/orders/{non_existent_ksuid}/ship")
    assert response.status_code == 404

async def test_ship_order_already_shipped(client: AsyncClient):
    inventory_item = await setup_test_inventory_item()
    order = await create_order_for_test(client, inventory_item.public_id, "Already Shipped User")

    # Ship it once
    await client.patch(f"/api/v1/orders/{order.public_id}/ship")

    # Try to ship again
    response = await client.patch(f"/api/v1/orders/{order.public_id}/ship")
    assert response.status_code == 400
    assert "already shipped" in response.json()["detail"].lower()

async def test_ship_order_cancelled(client: AsyncClient):
    inventory_item = await setup_test_inventory_item()
    order = await create_order_for_test(client, inventory_item.public_id, "Ship Cancelled User")

    # Cancel it first
    await client.patch(f"/api/v1/orders/{order.public_id}/cancel", json={"reason": "Test cancellation"})

    # Try to ship
    response = await client.patch(f"/api/v1/orders/{order.public_id}/ship")
    assert response.status_code == 400
    assert "cannot ship a cancelled order" in response.json()["detail"].lower()

# --- Tests for PATCH /orders/{order_public_id}/cancel ---

async def test_cancel_order_success_no_reason(client: AsyncClient):
    inventory_item = await setup_test_inventory_item()
    order = await create_order_for_test(client, inventory_item.public_id, "Cancel No Reason User")

    response = await client.patch(f"/api/v1/orders/{order.public_id}/cancel")
    assert response.status_code == 200
    data = response.json()

    assert data["public_id"] == order.public_id
    assert data["status"] == "cancelled"

    updated_order = await Order.get(public_id=order.public_id).prefetch_related("events")
    assert updated_order.status == "cancelled"
    cancelled_event = next((e for e in updated_order.events if e.event_type == "order_cancelled"), None)
    assert cancelled_event is not None
    assert cancelled_event.data == {"message": "Order marked as cancelled."}

async def test_cancel_order_success_with_reason(client: AsyncClient):
    inventory_item = await setup_test_inventory_item()
    order = await create_order_for_test(client, inventory_item.public_id, "Cancel With Reason User")

    cancel_payload = {"reason": "Customer changed mind"}
    response = await client.patch(f"/api/v1/orders/{order.public_id}/cancel", json=cancel_payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "cancelled"
    assert data["public_id"] == order.public_id

    updated_order_db = await Order.get(public_id=order.public_id).prefetch_related("events")
    assert updated_order_db.status == "cancelled"
    cancelled_event = next((e for e in updated_order_db.events if e.event_type == "order_cancelled"), None)
    assert cancelled_event is not None
    assert cancelled_event.data["reason"] == "Customer changed mind"

async def test_cancel_order_not_found(client: AsyncClient):
    non_existent_ksuid = generate_ksuid()
    response = await client.patch(f"/api/v1/orders/{non_existent_ksuid}/cancel")
    assert response.status_code == 404

async def test_cancel_order_already_cancelled(client: AsyncClient):
    inventory_item = await setup_test_inventory_item()
    order = await create_order_for_test(client, inventory_item.public_id, "Already Cancelled User")

    # Cancel it once
    await client.patch(f"/api/v1/orders/{order.public_id}/cancel")

    # Try to cancel again
    response = await client.patch(f"/api/v1/orders/{order.public_id}/cancel")
    assert response.status_code == 400
    assert "already cancelled" in response.json()["detail"].lower()

async def test_cancel_order_shipped_allowed_with_reason(client: AsyncClient):
    # Based on current router logic: shipped orders can be cancelled if a reason is provided.
    inventory_item = await setup_test_inventory_item()
    order = await create_order_for_test(client, inventory_item.public_id, "Cancel Shipped User")

    # Ship it first
    await client.patch(f"/api/v1/orders/{order.public_id}/ship", json={"tracking_number": "TRKSHIPFIRST"})

    # Try to cancel WITH a reason
    cancel_payload = {"reason": "Customer requested cancellation after shipping"}
    response = await client.patch(f"/api/v1/orders/{order.public_id}/cancel", json=cancel_payload)
    assert response.status_code == 200 # Current router logic allows this
    data = response.json()
    assert data["status"] == "cancelled"

    updated_order_db = await Order.get(public_id=order.public_id).prefetch_related("events")
    assert updated_order_db.status == "cancelled"
    cancelled_event = next((e for e in updated_order_db.events if e.event_type == "order_cancelled"), None)
    assert cancelled_event is not None
    assert cancelled_event.data["reason"] == "Customer requested cancellation after shipping"

async def test_cancel_order_shipped_allowed_no_reason(client: AsyncClient):
    # Based on current router logic: shipped orders can be cancelled even without a reason.
    inventory_item = await setup_test_inventory_item()
    order = await create_order_for_test(client, inventory_item.public_id, "Cancel Shipped No Reason User")

    # Ship it first
    await client.patch(f"/api/v1/orders/{order.public_id}/ship", json={"tracking_number": "TRKSHIPFIRSTNOREASON"})

    # Try to cancel WITHOUT a reason
    response = await client.patch(f"/api/v1/orders/{order.public_id}/cancel")
    assert response.status_code == 200 # Current router logic allows this
    data = response.json()
    assert data["status"] == "cancelled"

    updated_order_db = await Order.get(public_id=order.public_id).prefetch_related("events")
    assert updated_order_db.status == "cancelled"
    cancelled_event = next((e for e in updated_order_db.events if e.event_type == "order_cancelled"), None)
    assert cancelled_event is not None
    assert cancelled_event.data == {"message": "Order marked as cancelled."}


# To run these tests:
# Ensure pytest and pytest-asyncio are installed.
# From the project root (parent of 'backend'), run:
# PYTHONPATH=.:$PYTHONPATH pytest backend/tests
# or if using the app dir directly (less common for multi-component projects):
# pytest (from within backend dir, if PYTHONPATH is set up for backend.models etc.)
# Best practice is usually from project root with PYTHONPATH=.
