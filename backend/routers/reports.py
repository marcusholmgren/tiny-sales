# Previous imports remain the same...
import logging
from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List, Optional, Annotated
from tortoise.functions import Count # Sum, F, RawSQL, FloatField might not be needed here anymore for this specific function
from tortoise.expressions import Q # F might not be needed here anymore
# FloatField will be implicitly handled by Python's float type after DB retrieval
import datetime

from ..models import User, Order, OrderItem, InventoryItem, Category
# Removed Sum, F, RawSQL, FloatField from direct imports if only used in the modified part
# They might still be needed for other report functions.
from .. import auth
from ..schemas import (
    TimePeriodQuery,
    TotalSalesResponse,
    SalesByProductResponse,
    ProductSaleInfo,
    SalesByCategoryResponse,
    CategorySaleInfo,
    OrderStatusBreakdownResponse,
    OrderStatusCount,
    LowStockItemsResponse,
    LowStockItem, # Added LowStockItem
    MostStockedItemsResponse,
    MostStockedItem, # Added MostStockedItem
    InventoryValueResponse,
    InventoryValueItem # Added InventoryValueItem
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/reports",
    tags=["Reports"],
    dependencies=[Depends(auth.get_current_active_user)],
    responses={404: {"description": "Not found"}},
)

# ... existing sales report endpoints from previous step ...

# --- Sales Report Endpoints from previous step ---
# (Keep the previously implemented sales report endpoints here)
# 1. Total Sales Over Time
@router.get("/sales/total", response_model=TotalSalesResponse)
async def get_total_sales_report(
    current_user: Annotated[User, Depends(auth.get_current_active_user)],
    period: TimePeriodQuery = Depends()
):
    query = Order.filter(Q(status="shipped") | Q(status="completed"))
    if period.start_date:
        query = query.filter(created_at__gte=period.start_date)
    if period.end_date:
        query = query.filter(created_at__lt=period.end_date + datetime.timedelta(days=1))
    if current_user.role != "admin":
        query = query.filter(user_id=current_user.id)
    orders = await query.all()
    order_ids = [order.id for order in orders]
    
    if not order_ids:
        return TotalSalesResponse(total_revenue=0.0, item_count=0, order_count=0, start_date=period.start_date, end_date=period.end_date)

    # Fetch relevant OrderItem data for Python-side calculation
    items_data = await OrderItem.filter(order_id__in=order_ids).values(
        'price_at_purchase', 'quantity'
    )

    total_revenue = sum(
        item['price_at_purchase'] * item['quantity']
        for item in items_data
        if item['price_at_purchase'] is not None and item['quantity'] is not None
    )
    
    item_count = sum(item['quantity'] for item in items_data if item['quantity'] is not None)
    
    # order_count is len(orders) which is already calculated from the initial Order query.

    return TotalSalesResponse(
        total_revenue=float(total_revenue), # Ensure it's float
        item_count=item_count,
        order_count=len(orders), # Use the count of filtered orders
        start_date=period.start_date,
        end_date=period.end_date
    )

# 2. Sales by Product
@router.get("/sales/by-product", response_model=SalesByProductResponse)
async def get_sales_by_product_report(
    current_user: Annotated[User, Depends(auth.get_current_active_user)],
    period: TimePeriodQuery = Depends()
):
    order_filter = Q(order__status="shipped") | Q(order__status="completed")
    if period.start_date:
        order_filter &= Q(order__created_at__gte=period.start_date)
    if period.end_date:
        order_filter &= Q(order__created_at__lt=period.end_date + datetime.timedelta(days=1))
    if current_user.role != "admin":
        order_filter &= Q(order__user_id=current_user.id)

    product_sales_data = {}
    order_items = await OrderItem.filter(order_filter).prefetch_related('item').all()
    for oi in order_items:
        if not oi.item:
            logger.warning(f"OrderItem with ID {oi.id} has no associated item. Skipping in sales by product report.")
            continue
        product_id = oi.item.public_id
        product_name = oi.item.name
        if product_id not in product_sales_data:
            product_sales_data[product_id] = {"name": product_name, "quantity": 0, "revenue": 0.0}
        product_sales_data[product_id]["quantity"] += oi.quantity
        product_sales_data[product_id]["revenue"] += oi.quantity * oi.price_at_purchase

    response_items = [
        ProductSaleInfo(product_public_id=pid, product_name=data["name"], total_quantity_sold=data["quantity"], total_revenue=data["revenue"])
        for pid, data in product_sales_data.items()
    ]
    response_items.sort(key=lambda x: x.total_revenue, reverse=True)
    return SalesByProductResponse(products=response_items, start_date=period.start_date, end_date=period.end_date)

# 3. Sales by Category
@router.get("/sales/by-category", response_model=SalesByCategoryResponse)
async def get_sales_by_category_report(
    current_user: Annotated[User, Depends(auth.get_current_active_user)],
    period: TimePeriodQuery = Depends()
):
    order_filter = Q(order__status="shipped") | Q(order__status="completed")
    if period.start_date:
        order_filter &= Q(order__created_at__gte=period.start_date)
    if period.end_date:
        order_filter &= Q(order__created_at__lt=period.end_date + datetime.timedelta(days=1))
    if current_user.role != "admin":
        order_filter &= Q(order__user_id=current_user.id)

    order_items = await OrderItem.filter(order_filter).prefetch_related('item__category').all()
    category_sales_data = {}
    for oi in order_items:
        if not oi.item :
            logger.warning(f"OrderItem with ID {oi.id} has no associated item. Skipping in sales by category report.")
            continue

        cat_id = "uncategorized"
        cat_name = "Uncategorized"
        if oi.item.category:
            category = oi.item.category
            cat_id = category.public_id
            cat_name = category.name

        if cat_id not in category_sales_data:
            category_sales_data[cat_id] = {"name": cat_name, "quantity": 0, "revenue": 0.0}
        category_sales_data[cat_id]["quantity"] += oi.quantity
        category_sales_data[cat_id]["revenue"] += oi.quantity * oi.price_at_purchase

    response_items = [
        CategorySaleInfo(category_public_id=cid, category_name=data["name"], total_quantity_sold=data["quantity"], total_revenue=data["revenue"])
        for cid, data in category_sales_data.items()
    ]
    response_items.sort(key=lambda x: x.total_revenue, reverse=True)
    return SalesByCategoryResponse(categories=response_items, start_date=period.start_date, end_date=period.end_date)

# 4. Order Status Breakdown
@router.get("/orders/status-breakdown", response_model=OrderStatusBreakdownResponse)
async def get_order_status_breakdown_report(
    current_user: Annotated[User, Depends(auth.get_current_active_user)]
):
    query = Order.all()
    if current_user.role != "admin":
        query = query.filter(user_id=current_user.id)
    status_counts = await query.annotate(count=Count('id')).group_by('status').values('status', 'count')
    response_items = [
        OrderStatusCount(status=item['status'], count=item['count'])
        for item in status_counts if item['status']
    ]
    return OrderStatusBreakdownResponse(status_breakdown=response_items)


# --- Inventory Report Endpoints ---

# 5. Low Stock Items
@router.get("/inventory/low-stock", response_model=LowStockItemsResponse)
async def get_low_stock_items_report(
    current_user: Annotated[User, Depends(auth.get_current_active_admin_user)], # Admin only
    threshold: int = Query(10, ge=0, description="Stock quantity threshold for reporting low stock items.")
):
    """
    Lists products that are below a certain stock threshold.
    Requires admin privileges.
    """
    low_stock_query = InventoryItem.filter(quantity__lt=threshold, deleted_at__isnull=True).prefetch_related('category')
    items = await low_stock_query.all()

    response_items = [
        LowStockItem(
            product_public_id=item.public_id,
            product_name=item.name,
            current_quantity=item.quantity,
            category_name=item.category.name if item.category else None
        ) for item in items
    ]
    return LowStockItemsResponse(low_stock_items=response_items, threshold=threshold)

# 6. Most Stocked Items
@router.get("/inventory/most-stocked", response_model=MostStockedItemsResponse)
async def get_most_stocked_items_report(
    current_user: Annotated[User, Depends(auth.get_current_active_admin_user)], # Admin only
    limit: int = Query(10, ge=1, le=100, description="Number of most stocked items to retrieve.")
):
    """
    Shows products with the highest inventory levels.
    Requires admin privileges.
    """
    most_stocked_query = InventoryItem.filter(deleted_at__isnull=True).order_by('-quantity').limit(limit).prefetch_related('category')
    items = await most_stocked_query.all()

    response_items = [
        MostStockedItem(
            product_public_id=item.public_id,
            product_name=item.name,
            current_quantity=item.quantity,
            category_name=item.category.name if item.category else None
        ) for item in items
    ]
    return MostStockedItemsResponse(most_stocked_items=response_items, limit=limit)

# 7. Inventory Value
@router.get("/inventory/value", response_model=InventoryValueResponse)
async def get_inventory_value_report(
    current_user: Annotated[User, Depends(auth.get_current_active_admin_user)] # Admin only
):
    """
    Calculates the total value of your current inventory.
    Requires admin privileges.
    NOTE: This report currently assumes InventoryItem has a 'current_price' field.
          This field will be added in a subsequent step. Until then, price is assumed 0.
    """
    inventory_items = await InventoryItem.filter(deleted_at__isnull=True).all()

    total_value = 0.0
    value_items_breakdown = []

    for item in inventory_items:
        # TODO: Replace 0.0 with item.current_price once the field is added to InventoryItem model
        current_price = getattr(item, 'current_price', 0.0)
        item_total_value = item.quantity * current_price
        total_value += item_total_value

        value_items_breakdown.append(
            InventoryValueItem(
                product_public_id=item.public_id,
                product_name=item.name,
                current_quantity=item.quantity,
                current_price=current_price,
                total_value=item_total_value
            )
        )

    return InventoryValueResponse(
        total_inventory_value=total_value,
        items_contributing=value_items_breakdown,
        item_count=len(inventory_items)
    )
