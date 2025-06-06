# backend/tests/test_reports.py
import pytest
# from httpx import AsyncClient # No longer directly used in signatures
from fastapi.testclient import TestClient # Added for type hinting
from fastapi import status
import datetime

from ....features.auth.models import User
from ....features.inventory.models import Category, InventoryItem
from ....features.orders.models import Order, OrderItem, OrderEvent
from ....common.models import generate_ksuid
from ....features.reports.schemas import TimePeriodQuery # For constructing query params if needed

# Helper function to create auth headers
def get_auth_headers(token: str):
    return {"Authorization": f"Bearer {token}"}

@pytest.mark.asyncio
async def test_get_total_sales_report_as_admin(
    client: TestClient,
    test_user_admin_token: tuple[str, User],
    test_user_customer_token: tuple[str, User],
    clean_db_each_test  # Added the new fixture
):
    admin_token, admin_user = test_user_admin_token
    customer_token, customer_user = test_user_customer_token

    headers_admin = get_auth_headers(admin_token)
    headers_customer = get_auth_headers(customer_token)

    # Setup: Create some data
    cat, _ = await Category.update_or_create(name="Electronics Report Test", defaults={'description': 'Test desc'})
    item1, _ = await InventoryItem.update_or_create(name="Laptop Sales Report TSR", defaults={'quantity': 10, 'current_price': 1200.00, 'category_id': cat.id})
    item2, _ = await InventoryItem.update_or_create(name="Mouse Sales Report TSR", defaults={'quantity': 50, 'current_price': 25.00, 'category_id': cat.id})

    # Order 1 (Admin's order, completed) - using reportsadminuser
    order1_email = "reportsadmin_order1_tsr@example.com"
    order1_data = {"order_id": generate_ksuid(), "contact_name":"Reports Admin Order", "contact_email": order1_email, "delivery_address":"123 Reports Admin St", "status":"completed", "user_id":admin_user.id}
    order1, _ = await Order.update_or_create(contact_email=order1_email, defaults=order1_data)
    await OrderItem.filter(order_id=order1.id).delete() 
    await OrderItem.create(order_id=order1.id, item_id=item1.id, quantity=1, price_at_purchase=1200.00)
    await OrderItem.create(order_id=order1.id, item_id=item2.id, quantity=2, price_at_purchase=25.00)

    # Order 2 (Customer's order, shipped) - using reportscustomeruser
    order2_email = "reportscustomer_order2_tsr@example.com"
    order2_data = {"order_id": generate_ksuid(), "contact_name":"Reports Customer Order", "contact_email": order2_email, "delivery_address":"456 Reports Cust Rd", "status":"shipped", "user_id":customer_user.id}
    order2, _ = await Order.update_or_create(contact_email=order2_email, defaults=order2_data)
    await OrderItem.filter(order_id=order2.id).delete() 
    await OrderItem.create(order_id=order2.id, item_id=item1.id, quantity=1, price_at_purchase=1150.00)

    # Order 3 (Customer's order, pending - should not be counted) - using reportscustomeruser
    order3_email = "reportscustomer_order3_tsr@example.com"
    order3_data = {"order_id": generate_ksuid(), "contact_name":"Reports Customer Pending", "contact_email": order3_email, "delivery_address":"789 Reports Pend Ave", "status":"pending_payment", "user_id":customer_user.id}
    order3, _ = await Order.update_or_create(contact_email=order3_email, defaults=order3_data)
    await OrderItem.filter(order_id=order3.id).delete() 
    await OrderItem.create(order_id=order3.id, item_id=item2.id, quantity=5, price_at_purchase=30.00)

    # Test as Admin (sees all completed/shipped orders)
    response_admin = client.get("/api/v1/reports/sales/total", headers=headers_admin)
    assert response_admin.status_code == status.HTTP_200_OK
    data_admin = response_admin.json()
    assert data_admin["total_revenue"] == pytest.approx(1200.00 + 50.00 + 1150.00) 
    assert data_admin["item_count"] == 1 + 2 + 1 
    assert data_admin["order_count"] == 2

    # Test as Customer (sees only their own completed/shipped orders)
    response_customer = client.get("/api/v1/reports/sales/total", headers=headers_customer)
    assert response_customer.status_code == status.HTTP_200_OK
    data_customer = response_customer.json()
    assert data_customer["total_revenue"] == pytest.approx(1150.00)
    assert data_customer["item_count"] == 1
    assert data_customer["order_count"] == 1

    order1.created_at = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)
    await order1.save()
    order2.created_at = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)
    await order2.save()

    start_date = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    end_date = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
    response_admin_filtered = client.get( # Changed async_client to client
        f"/api/v1/reports/sales/total?start_date={start_date}&end_date={end_date}",
        headers=headers_admin
    )
    assert response_admin_filtered.status_code == status.HTTP_200_OK
    data_admin_filtered = response_admin_filtered.json()
    assert data_admin_filtered["total_revenue"] == pytest.approx(1200.00 + 50.00 + 1150.00)


@pytest.mark.asyncio
async def test_get_sales_by_product_report(client: TestClient, test_user_admin_token: tuple[str, User]): # Changed async_client
    admin_token, admin_user = test_user_admin_token
    headers = get_auth_headers(admin_token)

    cat, _ = await Category.update_or_create(name="Test Category for Product Sales Report")
    item_a, _ = await InventoryItem.update_or_create(name="Product A Sales Report SBP", defaults={'quantity':10, 'current_price':10.0, 'category_id': cat.id})
    item_b, _ = await InventoryItem.update_or_create(name="Product B Sales Report SBP", defaults={'quantity':5, 'current_price':20.0, 'category_id': cat.id})

    order_email_sbp = "psr_order_reportsadmin@example.com"
    order_data = {"order_id": generate_ksuid(), "contact_name":"Product Sales Order Report", "contact_email":order_email_sbp, "delivery_address":"1 St", "status":"shipped", "user_id":admin_user.id}
    order, _ = await Order.update_or_create(contact_email=order_email_sbp, defaults=order_data)

    await OrderItem.filter(order=order).delete()

    await OrderItem.create(order=order, item=item_a, quantity=3, price_at_purchase=10.0) # 30 for A in order1
    await OrderItem.create(order=order, item=item_b, quantity=2, price_at_purchase=20.0) # 40 for B in order1
    
    # Create a second order for the same admin user to test aggregation of the same product
    order2_email_sbp = "psr_order2_reportsadmin@example.com"
    order2_data = {"order_id": generate_ksuid(), "contact_name":"Product Sales Order Report 2", "contact_email":order2_email_sbp, "delivery_address":"1 St", "status":"completed", "user_id":admin_user.id}
    order2, _ = await Order.update_or_create(contact_email=order2_email_sbp, defaults=order2_data)
    await OrderItem.filter(order=order2).delete() # Clean items for idempotency for order2
    await OrderItem.create(order=order2, item=item_a, quantity=1, price_at_purchase=11.0) # 11 for A in order2

    response = client.get("/api/v1/reports/sales/by-product", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert len(data["products"]) >= 2 
    product_a_data = next((p for p in data["products"] if p["product_name"] == "Product A Sales Report SBP"), None)
    product_b_data = next((p for p in data["products"] if p["product_name"] == "Product B Sales Report SBP"), None)

    assert product_a_data is not None
    assert product_b_data is not None

    assert product_a_data["total_quantity_sold"] == 3 + 1
    assert product_a_data["total_revenue"] == pytest.approx(30.0 + 11.0)
    assert product_b_data["total_quantity_sold"] == 2
    assert product_b_data["total_revenue"] == pytest.approx(40.0)

    test_product_names = {"Product A Sales Report SBP", "Product B Sales Report SBP"}
    test_products_data = [p for p in data["products"] if p["product_name"] in test_product_names]

    revenues = [p['total_revenue'] for p in test_products_data]
    assert revenues == sorted(revenues, reverse=True)
    assert test_products_data[0]["product_name"] == "Product A Sales Report SBP" 
    assert test_products_data[1]["product_name"] == "Product B Sales Report SBP" 

@pytest.mark.asyncio
async def test_get_sales_by_category_report(client: TestClient, test_user_admin_token: tuple[str, User]): # Changed async_client
    admin_token, admin_user = test_user_admin_token
    headers = get_auth_headers(admin_token)

    cat_electronics, _ = await Category.update_or_create(name="Electronics Category Sales Report SBC")
    cat_books, _ = await Category.update_or_create(name="Books Category Sales Report SBC")
    item_e, _ = await InventoryItem.update_or_create(name="Gadget Sales Report SBC", defaults={'quantity': 5, 'current_price':100.0, 'category_id': cat_electronics.id})
    item_b, _ = await InventoryItem.update_or_create(name="Novel Sales Report SBC", defaults={'quantity': 10, 'current_price':15.0, 'category_id': cat_books.id})

    order_email_sbc = "csr_order_reportsadmin@example.com"
    order_data = {"order_id": generate_ksuid(), "contact_name":"Cat Sales Order Report", "contact_email":order_email_sbc, "delivery_address":"1 St", "status":"completed", "user_id":admin_user.id}
    order, _ = await Order.update_or_create(contact_email=order_email_sbc, defaults=order_data)
    await OrderItem.filter(order=order).delete() 

    await OrderItem.create(order=order, item=item_e, quantity=2, price_at_purchase=100.0) 
    await OrderItem.create(order=order, item=item_b, quantity=3, price_at_purchase=15.0)  

    response = client.get("/api/v1/reports/sales/by-category", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    electronics_data = next((c for c in data["categories"] if c["category_name"] == "Electronics Category Sales Report SBC"), None)
    books_data = next((c for c in data["categories"] if c["category_name"] == "Books Category Sales Report SBC"), None)

    assert electronics_data is not None
    assert books_data is not None

    assert electronics_data["total_quantity_sold"] == 2
    assert electronics_data["total_revenue"] == pytest.approx(200.0)
    assert books_data["total_quantity_sold"] == 3
    assert books_data["total_revenue"] == pytest.approx(45.0)

    test_cat_names = {"Electronics Category Sales Report SBC", "Books Category Sales Report SBC"}
    test_cats_data = [c for c in data["categories"] if c["category_name"] in test_cat_names]
    revenues = [c['total_revenue'] for c in test_cats_data]
    assert revenues == sorted(revenues, reverse=True)
    assert test_cats_data[0]['category_name'] == "Electronics Category Sales Report SBC"
    assert test_cats_data[1]['category_name'] == "Books Category Sales Report SBC"


@pytest.mark.asyncio
async def test_get_order_status_breakdown_report(client: TestClient, test_user_admin_token: tuple[str, User]): # Changed async_client
    admin_token, admin_user = test_user_admin_token
    headers = get_auth_headers(admin_token)

    defaults_s1 = {"order_id": generate_ksuid(), "contact_name":"Order S1 OSBR", "delivery_address":".", "status":"shipped", "user_id":admin_user.id, "contact_email":"s1_osbr_reportsadmin@example.com"}
    await Order.update_or_create(contact_email="s1_osbr_reportsadmin@example.com", defaults=defaults_s1)
    
    defaults_s2 = {"order_id": generate_ksuid(), "contact_name":"Order S2 OSBR", "delivery_address":".", "status":"shipped", "user_id":admin_user.id, "contact_email":"s2_osbr_reportsadmin@example.com"}
    await Order.update_or_create(contact_email="s2_osbr_reportsadmin@example.com", defaults=defaults_s2)
    
    defaults_c1 = {"order_id": generate_ksuid(), "contact_name":"Order C1 OSBR", "delivery_address":".", "status":"completed", "user_id":admin_user.id, "contact_email":"c1_osbr_reportsadmin@example.com"}
    await Order.update_or_create(contact_email="c1_osbr_reportsadmin@example.com", defaults=defaults_c1)
    
    defaults_p1 = {"order_id": generate_ksuid(), "contact_name":"Order P1 OSBR", "delivery_address":".", "status":"pending_payment", "user_id":admin_user.id, "contact_email":"p1_osbr_reportsadmin@example.com"}
    await Order.update_or_create(contact_email="p1_osbr_reportsadmin@example.com", defaults=defaults_p1)

    response = client.get("/api/v1/reports/orders/status-breakdown", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    status_map = {item["status"]: item["count"] for item in data["status_breakdown"]}
    assert status_map.get("shipped", 0) >= 2 
    assert status_map.get("completed", 0) >= 1
    assert status_map.get("pending_payment", 0) >= 1


@pytest.mark.asyncio
async def test_get_low_stock_items_report(client: TestClient, test_user_admin_token: tuple[str, User]): # Changed async_client
    admin_token, _ = test_user_admin_token 
    headers = get_auth_headers(admin_token)
    cat, _ = await Category.update_or_create(name="LowStock Category Report LSIR")

    await InventoryItem.update_or_create(name="Low Item 1 Report LSIR", defaults={"quantity":5, "current_price":10.0, "category_id":cat.id})
    await InventoryItem.update_or_create(name="Low Item 2 Report LSIR", defaults={"quantity":15, "current_price":10.0, "category_id":cat.id}) 
    await InventoryItem.update_or_create(name="Low Item 3 Report LSIR", defaults={"quantity":2, "current_price":10.0, "category_id":cat.id})

    response = client.get("/api/v1/reports/inventory/low-stock?threshold=10", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["threshold"] == 10
    
    test_item_names_in_report = {item["product_name"] for item in data["low_stock_items"]}
    
    assert "Low Item 1 Report LSIR" in test_item_names_in_report
    assert "Low Item 3 Report LSIR" in test_item_names_in_report
    assert "Low Item 2 Report LSIR" not in test_item_names_in_report 
    
    relevant_items_count = sum(1 for name in test_item_names_in_report if "LSIR" in name)
    assert relevant_items_count == 2


@pytest.mark.asyncio
async def test_get_most_stocked_items_report(client: TestClient, test_user_admin_token: tuple[str, User]): # Changed async_client
    admin_token, _ = test_user_admin_token
    headers = get_auth_headers(admin_token)
    cat, _ = await Category.update_or_create(name="MostStocked Category Report MSIR")
    # Using very high quantities to ensure these items are top, overriding potential leakage
    await InventoryItem.update_or_create(name="Stock Item A Report MSIR", defaults={"quantity":10000, "current_price":1.0, "category_id":cat.id})
    await InventoryItem.update_or_create(name="Stock Item B Report MSIR", defaults={"quantity":20000, "current_price":1.0, "category_id":cat.id})
    await InventoryItem.update_or_create(name="Stock Item C Report MSIR", defaults={"quantity":5000, "current_price":1.0, "category_id":cat.id})

    response = client.get("/api/v1/reports/inventory/most-stocked?limit=2", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["limit"] == 2
    assert len(data["most_stocked_items"]) == 2 
    
    response_item_names = {item['product_name'] for item in data['most_stocked_items']}
    assert "Stock Item B Report MSIR" in response_item_names
    assert "Stock Item A Report MSIR" in response_item_names
    assert data["most_stocked_items"][0]["product_name"] == "Stock Item B Report MSIR"
    assert data["most_stocked_items"][1]["product_name"] == "Stock Item A Report MSIR"


@pytest.mark.asyncio
async def test_get_inventory_value_report(client: TestClient, test_user_admin_token: tuple[str, User]): # Changed async_client
    admin_token, _ = test_user_admin_token
    headers = get_auth_headers(admin_token)
    cat, _ = await Category.update_or_create(name="Value Category Report IVR")

    item_x, _ = await InventoryItem.update_or_create(name="Value Item X Report IVR", defaults={"quantity":10, "current_price":2.50, "category_id":cat.id}) 
    item_y, _ = await InventoryItem.update_or_create(name="Value Item Y Report IVR", defaults={"quantity":5, "current_price":10.00, "category_id":cat.id}) 
    await InventoryItem.update_or_create(name="Value Item Z Report IVR (Zero Price)", defaults={"quantity":100, "current_price":0.0, "category_id":cat.id})
    await InventoryItem.update_or_create(name="Value Item W Report IVR (Zero Quantity)", defaults={"quantity":0, "current_price":100.0, "category_id":cat.id})

    response = client.get("/api/v1/reports/inventory/value", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    item_x_data = next((item for item in data["items_contributing"] if item["product_name"] == "Value Item X Report IVR"), None)
    item_y_data = next((item for item in data["items_contributing"] if item["product_name"] == "Value Item Y Report IVR"), None)

    assert item_x_data is not None
    assert item_y_data is not None

    assert item_x_data["current_price"] == pytest.approx(2.50)
    assert item_y_data["current_price"] == pytest.approx(10.00)
    
    assert item_x_data["total_value"] == pytest.approx(25.0)
    assert item_y_data["total_value"] == pytest.approx(50.0)

    test_specific_items_value = 0
    for item in data["items_contributing"]:
        if "IVR" in item["product_name"]: 
            test_specific_items_value += item["total_value"]
            
    assert data["total_inventory_value"] >= test_specific_items_value
    calculated_total_value_from_response = sum(i['total_value'] for i in data['items_contributing'])
    assert data["total_inventory_value"] == pytest.approx(calculated_total_value_from_response)

    count_of_ivr_items_in_report = sum(1 for item in data["items_contributing"] if "IVR" in item["product_name"])
    assert count_of_ivr_items_in_report >= 4 

    assert data["item_count"] >= 4


@pytest.mark.asyncio
async def test_report_auth_required(client: TestClient): # Changed async_client
    endpoints = [
        "/api/v1/reports/sales/total",
        "/api/v1/reports/sales/by-product",
        "/api/v1/reports/sales/by-category",
        "/api/v1/reports/orders/status-breakdown",
        "/api/v1/reports/inventory/low-stock",
        "/api/v1/reports/inventory/most-stocked",
        "/api/v1/reports/inventory/value",
    ]
    for endpoint in endpoints:
        response = client.get(endpoint) # Corrected: no await, uses client
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

# More tests could be added for:
# - Empty database scenarios for each report.
# - Specific date range filtering edge cases.
# - Authorization: Non-admin user trying to access admin-only inventory reports (e.g. using customer_token for /inventory/low-stock)
# - Pagination if it were added to any reports.
