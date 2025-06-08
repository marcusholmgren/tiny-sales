import pytest
from fastapi.testclient import TestClient

# Assuming models and schemas might be needed for direct assertions or setup
from app.features.orders.models import Order, OrderItem, OrderEvent
from app.features.inventory.models import InventoryItem
from app.common.models import generate_ksuid
from app.features.orders.schemas import OrderPublicSchema # Assuming this exists or will be created
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
    assert "already cancelled" in response.json()["detail"].lower()

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
    assert "stock_replenished" in cancelled_event.data
    assert cancelled_event.data["stock_replenished"] is True

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
    assert data["detail"] == "Shipped order cancellation requires reason." # Match actual error message

    updated_order_db = await Order.get(public_id=order.public_id).prefetch_related("events")
    assert updated_order_db.status == "shipped" # Order should remain shipped
    cancelled_event = next((e for e in updated_order_db.events if e.event_type == "order_cancelled"), None)
    assert cancelled_event is None # No cancellation event should be created

# --- Tests for GET /orders/ (List Orders with Status Filtering) ---

async def create_order_with_status(
    client_fixture: TestClient, # Use the client fixture (client or admin_client)
    user_id: str, # The user_id of the user to associate the order with
    inventory_item_public_id: str,
    status: str,
    contact_name: str = "Order User"
) -> OrderPublicSchema:
    """Helper to create an order and then update its status."""
    # Create the order - assuming create_order_for_test uses the token from client_fixture
    # If create_order_for_test doesn't directly support associating with a *different* user_id
    # than the one in client_fixture's token, this needs adjustment.
    # For now, assuming orders are created by the user whose token is in client_fixture.
    # The 'user_id' param here is more for tracking/knowing which user it *should* belong to.

    # Use the provided client_fixture to make the request
    # The original create_order_for_test uses its own token logic.
    # We need to ensure the order is created by the correct user for user-specific tests.
    # Let's simplify and assume the client_fixture IS for the user we want to create the order for.

    order_payload = {
        "contact_name": contact_name,
        "contact_email": f"{contact_name.lower().replace(' ', '')}@example.com",
        "delivery_address": "123 Test Order St",
        "items": [
            {
                "product_public_id": inventory_item_public_id,
                "quantity": 1,
                "price_at_purchase": 25.00
            }
        ]
    }
    # Use client_fixture's headers if they are set up for auth, otherwise, this won't work as intended
    # The existing conftest.py sets up client and admin_client with tokens.
    response = client_fixture.post("/api/v1/orders/", json=order_payload)
    assert response.status_code == 201, f"Failed to create order: {response.text}"
    created_order_data = response.json()
    order_public_id = created_order_data["public_id"]

    # Fetch the full order object from DB to update status
    order_db = await Order.get(public_id=order_public_id)
    order_db.status = status
    # If the order is created by one user (e.g. admin) but should be "owned" by another for testing,
    # we might need to update user_id here, assuming test_user and admin_user fixtures provide User objects.
    # For now, the router assigns user_id based on current_user from token.
    # So, client_fixture must be the one for the intended user.
    # The user_id parameter in this helper is thus somewhat redundant if client_fixture dictates the user.
    # However, it's good for clarity in test setup.
    await order_db.save(update_fields=['status'])

    # Re-fetch or use the initially returned data and just update status for the schema
    created_order_data["status"] = status
    return OrderPublicSchema(**created_order_data)


async def test_list_orders_no_status_filter_user(client: TestClient, test_user, admin_user):
    inv_item1 = await setup_test_inventory_item()
    inv_item2 = await setup_test_inventory_item()

    # Orders for test_user (client makes requests as test_user)
    order_u1_s1 = await create_order_with_status(client, test_user.id, inv_item1.public_id, "placed", "User1 Order1")
    order_u1_s2 = await create_order_with_status(client, test_user.id, inv_item2.public_id, "shipped", "User1 Order2")

    # Order for another user (admin_user, created by admin_client)
    # This setup assumes admin_client fixture is available from conftest.py
    # and is authenticated as an admin user.
    # Also assumes test_user and admin_user fixtures provide User model instances or similar.
    # For this test, we only care about what 'client' (test_user) sees.
    # So, creating an order for admin_user is just to ensure it's NOT returned.
    # This requires admin_client to be a fixture. If not, this line needs to be adapted or removed.
    # For now, let's assume conftest.py provides admin_client.
    # We'd also need an admin_user object.
    # If admin_client is not available, we skip creating other user's order.
    # The important part is test_user only sees their own.

    response = client.get("/api/v1/orders/")
    assert response.status_code == 200, response.text
    data = response.json()
    order_ids_returned = {order["public_id"] for order in data}

    assert len(data) == 2
    assert order_u1_s1.public_id in order_ids_returned
    assert order_u1_s2.public_id in order_ids_returned


async def test_list_orders_no_status_filter_admin(admin_client: TestClient, test_user, admin_user):
    inv_item1 = await setup_test_inventory_item()
    inv_item2 = await setup_test_inventory_item()
    inv_item3 = await setup_test_inventory_item()

    # Order for test_user (created by test_user's client, then fetched by admin)
    # This requires a 'client' fixture that is separate from 'admin_client'.
    # We'll assume 'client' is available from conftest.py for test_user.
    # This is a bit tricky if create_order_with_status uses the client_fixture's auth.
    # For admin to see all, orders need to exist. Let's assume admin_client can create orders for any user,
    # or we use the specific user's client to create them.
    # Simplest: admin_client creates all orders, but we need to correctly assign user_id if that's possible via API,
    # or acknowledge they will all be owned by admin if not.
    # The current Order.create in router assigns user from current_user.
    # So, to have orders by different users, they must be created by those users.
    # Let's use the client fixtures directly.

    # Order for test_user (using client for test_user)
    # This requires 'client' fixture to be passed or available.
    # We need to get a non-admin client here.
    # This test structure relies heavily on fixtures from conftest.py (client, admin_client, test_user, admin_user)

    # Re-thinking: create_order_with_status takes client_fixture.
    # So, for test_user's order, pass 'client'. For admin_user's order, pass 'admin_client'.

    # Order for test_user (client makes requests as test_user)
    # We need a regular client fixture, let's assume 'client' is it.
    # This test is for admin_client, so it will make the GET request.
    # The orders can be created by anyone.

    # Assume test_user_client and admin_user_client for clarity in creating orders
    # For the actual test, we use admin_client to list.
    # This means we need a way to get a client for a regular user if test_user_client is not a fixture.
    # The `client` fixture is typically the regular user.

    # Order for User1 (using regular 'client' fixture)
    order_u1_s1 = await create_order_with_status(client, test_user.id, inv_item1.public_id, "placed", "User1 Order Placed")
    # Order for Admin (using 'admin_client' fixture, assuming admin can also have orders)
    order_admin_s1 = await create_order_with_status(admin_client, admin_user.id, inv_item2.public_id, "shipped", "Admin Order Shipped")
    order_admin_s2 = await create_order_with_status(admin_client, admin_user.id, inv_item3.public_id, "cancelled", "Admin Order Cancelled")


    response = admin_client.get("/api/v1/orders/")
    assert response.status_code == 200, response.text
    data = response.json()
    order_ids_returned = {order["public_id"] for order in data}

    # Admin should see all orders created in this scope
    assert len(data) >= 3 # Could be more if other tests created orders not cleaned up
    assert order_u1_s1.public_id in order_ids_returned
    assert order_admin_s1.public_id in order_ids_returned
    assert order_admin_s2.public_id in order_ids_returned


async def test_list_orders_single_status_filter_user(client: TestClient, test_user):
    inv_item1 = await setup_test_inventory_item()
    inv_item2 = await setup_test_inventory_item()

    order_u1_placed = await create_order_with_status(client, test_user.id, inv_item1.public_id, "placed", "User Placed")
    order_u1_shipped = await create_order_with_status(client, test_user.id, inv_item2.public_id, "shipped", "User Shipped")

    response = client.get("/api/v1/orders/?statuses=placed")
    assert response.status_code == 200, response.text
    data = response.json()
    order_ids_returned = {order["public_id"] for order in data}

    assert len(data) == 1
    assert order_u1_placed.public_id in order_ids_returned
    assert order_u1_shipped.public_id not in order_ids_returned
    assert data[0]["status"] == "placed"


async def test_list_orders_single_status_filter_admin(admin_client: TestClient, client: TestClient, test_user, admin_user):
    inv_item1 = await setup_test_inventory_item()
    inv_item2 = await setup_test_inventory_item()
    inv_item3 = await setup_test_inventory_item()

    order_u1_placed = await create_order_with_status(client, test_user.id, inv_item1.public_id, "placed", "User Placed")
    order_admin_shipped = await create_order_with_status(admin_client, admin_user.id, inv_item2.public_id, "shipped", "Admin Shipped")
    order_u1_shipped_too = await create_order_with_status(client, test_user.id, inv_item3.public_id, "shipped", "User Shipped Too")

    response = admin_client.get("/api/v1/orders/?statuses=shipped")
    assert response.status_code == 200, response.text
    data = response.json()
    order_ids_returned = {order["public_id"] for order in data}

    assert len(data) == 2
    assert order_admin_shipped.public_id in order_ids_returned
    assert order_u1_shipped_too.public_id in order_ids_returned
    assert order_u1_placed.public_id not in order_ids_returned
    for order_data in data:
        assert order_data["status"] == "shipped"

async def test_list_orders_multiple_status_filter_user(client: TestClient, test_user):
    inv_item1 = await setup_test_inventory_item()
    inv_item2 = await setup_test_inventory_item()
    inv_item3 = await setup_test_inventory_item()

    order_u1_placed = await create_order_with_status(client, test_user.id, inv_item1.public_id, "placed", "User Placed")
    order_u1_shipped = await create_order_with_status(client, test_user.id, inv_item2.public_id, "shipped", "User Shipped")
    order_u1_cancelled = await create_order_with_status(client, test_user.id, inv_item3.public_id, "cancelled", "User Cancelled")

    response = client.get("/api/v1/orders/?statuses=placed&statuses=shipped")
    assert response.status_code == 200, response.text
    data = response.json()
    order_ids_returned = {order["public_id"] for order in data}
    statuses_returned = {order["status"] for order in data}

    assert len(data) == 2
    assert order_u1_placed.public_id in order_ids_returned
    assert order_u1_shipped.public_id in order_ids_returned
    assert order_u1_cancelled.public_id not in order_ids_returned
    assert "placed" in statuses_returned
    assert "shipped" in statuses_returned
    assert "cancelled" not in statuses_returned


async def test_list_orders_multiple_status_filter_admin(admin_client: TestClient, client: TestClient, test_user, admin_user):
    inv_item1 = await setup_test_inventory_item()
    inv_item2 = await setup_test_inventory_item()
    inv_item3 = await setup_test_inventory_item()
    inv_item4 = await setup_test_inventory_item()

    order_u1_placed = await create_order_with_status(client, test_user.id, inv_item1.public_id, "placed", "User Placed")
    order_admin_cancelled = await create_order_with_status(admin_client, admin_user.id, inv_item2.public_id, "cancelled", "Admin Cancelled")
    order_u1_shipped = await create_order_with_status(client, test_user.id, inv_item3.public_id, "shipped", "User Shipped")
    order_admin_placed_too = await create_order_with_status(admin_client, admin_user.id, inv_item4.public_id, "placed", "Admin Placed Too")


    response = admin_client.get("/api/v1/orders/?statuses=placed&statuses=cancelled")
    assert response.status_code == 200, response.text
    data = response.json()
    order_ids_returned = {order["public_id"] for order in data}
    statuses_returned = {order["status"] for order in data}

    assert len(data) == 3 # order_u1_placed, order_admin_cancelled, order_admin_placed_too
    assert order_u1_placed.public_id in order_ids_returned
    assert order_admin_cancelled.public_id in order_ids_returned
    assert order_admin_placed_too.public_id in order_ids_returned
    assert order_u1_shipped.public_id not in order_ids_returned
    assert "placed" in statuses_returned
    assert "cancelled" in statuses_returned
    assert "shipped" not in statuses_returned


async def test_list_orders_status_filter_no_match_user(client: TestClient, test_user):
    inv_item1 = await setup_test_inventory_item()
    await create_order_with_status(client, test_user.id, inv_item1.public_id, "placed", "User Placed")

    response = client.get("/api/v1/orders/?statuses=delivered")
    assert response.status_code == 200, response.text
    data = response.json()
    assert len(data) == 0

async def test_list_orders_status_filter_no_match_admin(admin_client: TestClient, client: TestClient, test_user):
    inv_item1 = await setup_test_inventory_item()
    await create_order_with_status(client, test_user.id, inv_item1.public_id, "placed", "User Placed")

    response = admin_client.get("/api/v1/orders/?statuses=nonexistentstatus")
    assert response.status_code == 200, response.text
    data = response.json()
    assert len(data) == 0

async def test_list_orders_status_filter_empty_string_admin(admin_client: TestClient, client: TestClient, test_user, admin_user):
    # Test that an empty statuses string is treated as no filter
    inv_item1 = await setup_test_inventory_item()
    inv_item2 = await setup_test_inventory_item()

    order_u1_s1 = await create_order_with_status(client, test_user.id, inv_item1.public_id, "placed", "User1 Order1 Empty String")
    order_admin_s1 = await create_order_with_status(admin_client, admin_user.id, inv_item2.public_id, "shipped", "Admin Order1 Empty String")

    response = admin_client.get("/api/v1/orders/?statuses=") # Empty status query
    assert response.status_code == 200, response.text
    data = response.json()
    order_ids_returned = {order["public_id"] for order in data}

    assert len(data) >= 2 # Should return all orders visible to admin
    assert order_u1_s1.public_id in order_ids_returned
    assert order_admin_s1.public_id in order_ids_returned

async def test_list_orders_status_filter_with_spaces_user(client: TestClient, test_user):
    inv_item1 = await setup_test_inventory_item()
    inv_item2 = await setup_test_inventory_item()

    order_u1_placed = await create_order_with_status(client, test_user.id, inv_item1.public_id, "placed", "User Placed Spaces")
    order_u1_shipped = await create_order_with_status(client, test_user.id, inv_item2.public_id, "shipped", "User Shipped Spaces")

    response = client.get("/api/v1/orders/?statuses=%20placed%20&statuses=%20shipped%20") # Statuses with spaces
    assert response.status_code == 200, response.text
    data = response.json()
    order_ids_returned = {order["public_id"] for order in data}
    statuses_returned = {order["status"] for order in data}

    assert len(data) == 2
    assert order_u1_placed.public_id in order_ids_returned
    assert order_u1_shipped.public_id in order_ids_returned
    assert "placed" in statuses_returned
    assert "shipped" in statuses_returned


# To run these tests:
# Ensure pytest, pytest-asyncio, and httpx are installed.
# From the project root (parent of 'backend'), run:
# PYTHONPATH=. pytest backend/tests/test_orders.py
# (or simply `pytest` if your project structure and pytest.ini/pyproject.toml are set up for discovery)

# Fixture usage note:
# These tests assume `client` (for a regular authenticated user), `admin_client` (for an admin authenticated user),
# `test_user` (model/object for the regular user), and `admin_user` (model/object for the admin user)
# are provided by conftest.py or a similar mechanism.
# The `create_order_with_status` helper uses the passed client_fixture (e.g. `client` or `admin_client`)
# to create orders, so the order's `user_id` will be that of the authenticated user for that client.
