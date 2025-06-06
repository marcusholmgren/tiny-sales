"""
Reports Service Module

This module provides a collection of functions for generating various business reports
for the Tiny Sales application. Reports include sales analytics, inventory status,
and order breakdowns.
"""

import datetime
import logging
from typing import List, Optional
from tortoise.functions import Count
from tortoise.expressions import Q

# Models from other features
from ..auth.models import User as AuthUser
from ..orders.models import Order, OrderItem
from ..inventory.models import (InventoryItem, Category)

# Schemas for response construction (used internally by service, or router maps to them)
from .schemas import (
    TotalSalesResponse, ProductSaleInfo, SalesByProductResponse,
    CategorySaleInfo, SalesByCategoryResponse, OrderStatusCount,
    OrderStatusBreakdownResponse, LowStockItem, LowStockItemsResponse,
    MostStockedItem, MostStockedItemsResponse, InventoryValueItem,
    InventoryValueResponse
)

logger = logging.getLogger(__name__)

async def generate_total_sales_report(
    current_user: AuthUser,
    start_date: Optional[datetime.date],
    end_date: Optional[datetime.date]
) -> TotalSalesResponse:
    """
    Generates a report of total sales statistics.
    
    This function calculates the total revenue, item count, and order count for completed and
    shipped orders within the specified date range. For non-admin users, only their own orders
    are included.
    
    Args:
        current_user: The authenticated user requesting the report
        start_date: Optional start date for filtering orders (inclusive)
        end_date: Optional end date for filtering orders (inclusive)
        
    Returns:
        TotalSalesResponse: An object containing aggregated sales statistics including:
            - total_revenue: Sum of all items' price_at_purchase * quantity
            - item_count: Total number of items sold
            - order_count: Number of orders included in the calculation
            - start_date: The start date used for filtering (if provided)
            - end_date: The end date used for filtering (if provided)
    """
    query = Order.filter(Q(status="shipped") | Q(status="completed")) # Corrected status from previous example
    if start_date:
        query = query.filter(created_at__gte=start_date)
    if end_date:
        # Add 1 day to end_date to make it inclusive for date range queries
        query = query.filter(created_at__lt=end_date + datetime.timedelta(days=1))

    if current_user.role != "admin":
        query = query.filter(user_id=current_user.id)

    orders = await query.all()
    order_ids = [order.id for order in orders]

    if not order_ids:
        return TotalSalesResponse(total_revenue=0.0, item_count=0, order_count=0, start_date=start_date, end_date=end_date)

    items_data = await OrderItem.filter(order_id__in=order_ids).values('price_at_purchase', 'quantity')
    total_revenue = sum(item['price_at_purchase'] * item['quantity'] for item in items_data if item['price_at_purchase'] is not None and item['quantity'] is not None)
    item_count = sum(item['quantity'] for item in items_data if item['quantity'] is not None)

    return TotalSalesResponse(
        total_revenue=float(total_revenue), item_count=item_count, order_count=len(orders),
        start_date=start_date, end_date=end_date
    )

async def generate_sales_by_product_report(
    current_user: AuthUser,
    start_date: Optional[datetime.date],
    end_date: Optional[datetime.date]
) -> SalesByProductResponse:
    """
    Generates a sales report broken down by product.
    
    This function analyzes order items to calculate sales metrics for each product,
    including total quantity sold and revenue generated. Results are sorted by revenue 
    in descending order. For non-admin users, only their own orders are included.
    
    Args:
        current_user: The authenticated user requesting the report
        start_date: Optional start date for filtering orders (inclusive)
        end_date: Optional end date for filtering orders (inclusive)
        
    Returns:
        SalesByProductResponse: An object containing:
            - products: List of ProductSaleInfo objects with sales data per product
            - start_date: The start date used for filtering (if provided)
            - end_date: The end date used for filtering (if provided)
            
    Note:
        Each ProductSaleInfo includes product_public_id, product_name,
        total_quantity_sold, and total_revenue.
    """
    order_filter = Q(order__status="shipped") | Q(order__status="completed")
    if start_date:
        order_filter &= Q(order__created_at__gte=start_date)
    if end_date:
        order_filter &= Q(order__created_at__lt=end_date + datetime.timedelta(days=1))
    if current_user.role != "admin":
        order_filter &= Q(order__user_id=current_user.id)

    product_sales_data = {}
    order_items = await OrderItem.filter(order_filter).prefetch_related('item').all()
    for oi in order_items:
        if not oi.item: continue
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
    return SalesByProductResponse(products=response_items, start_date=start_date, end_date=end_date)

async def generate_sales_by_category_report(
    current_user: AuthUser,
    start_date: Optional[datetime.date],
    end_date: Optional[datetime.date]
) -> SalesByCategoryResponse:
    """
    Generates a sales report broken down by product category.
    
    This function analyzes order items to calculate sales metrics for each product category,
    including total quantity sold and revenue generated. Results are sorted by revenue
    in descending order. For non-admin users, only their own orders are included.
    Items without a category are grouped under "Uncategorized".
    
    Args:
        current_user: The authenticated user requesting the report
        start_date: Optional start date for filtering orders (inclusive)
        end_date: Optional end date for filtering orders (inclusive)
        
    Returns:
        SalesByCategoryResponse: An object containing:
            - categories: List of CategorySaleInfo objects with sales data per category
            - start_date: The start date used for filtering (if provided)
            - end_date: The end date used for filtering (if provided)
            
    Note:
        Each CategorySaleInfo includes category_public_id, category_name,
        total_quantity_sold, and total_revenue.
    """
    order_filter = Q(order__status="shipped") | Q(order__status="completed")
    if start_date:
        order_filter &= Q(order__created_at__gte=start_date)
    if end_date:
        order_filter &= Q(order__created_at__lt=end_date + datetime.timedelta(days=1))
    if current_user.role != "admin":
        order_filter &= Q(order__user_id=current_user.id)

    order_items = await OrderItem.filter(order_filter).prefetch_related('item__category').all()
    category_sales_data = {}
    for oi in order_items:
        if not oi.item: continue
        cat_id, cat_name = ("uncategorized", "Uncategorized")
        if oi.item.category:
            cat_id, cat_name = (oi.item.category.public_id, oi.item.category.name)

        if cat_id not in category_sales_data:
            category_sales_data[cat_id] = {"name": cat_name, "quantity": 0, "revenue": 0.0}
        category_sales_data[cat_id]["quantity"] += oi.quantity
        category_sales_data[cat_id]["revenue"] += oi.quantity * oi.price_at_purchase

    response_items = [
        CategorySaleInfo(category_public_id=cid, category_name=data["name"], total_quantity_sold=data["quantity"], total_revenue=data["revenue"])
        for cid, data in category_sales_data.items()
    ]
    response_items.sort(key=lambda x: x.total_revenue, reverse=True)
    return SalesByCategoryResponse(categories=response_items, start_date=start_date, end_date=end_date)

async def generate_order_status_breakdown_report(current_user: AuthUser) -> OrderStatusBreakdownResponse:
    """
    Generates a report showing the count of orders by status.
    
    This function provides insight into how many orders are in each status
    (e.g., placed, shipped, completed, cancelled). For non-admin users,
    only their own orders are included in the counts.
    
    Args:
        current_user: The authenticated user requesting the report
        
    Returns:
        OrderStatusBreakdownResponse: An object containing:
            - status_breakdown: List of OrderStatusCount objects where each object
              contains a status name and the count of orders with that status
    
    Note:
        Orders with null status are excluded from the report.
    """
    query = Order.all()
    if current_user.role != "admin":
        query = query.filter(user_id=current_user.id)
    status_counts = await query.annotate(count=Count('id')).group_by('status').values('status', 'count')
    response_items = [OrderStatusCount(status=item['status'], count=item['count']) for item in status_counts if item['status']]
    return OrderStatusBreakdownResponse(status_breakdown=response_items)

async def generate_low_stock_items_report(threshold: int) -> LowStockItemsResponse:
    """
    Generates a report of inventory items with stock levels below a specified threshold.
    
    This function helps identify products that may need to be reordered soon.
    It only includes active (non-deleted) items.
    
    Args:
        threshold: The quantity threshold below which items are considered low in stock
        
    Returns:
        LowStockItemsResponse: An object containing:
            - low_stock_items: List of LowStockItem objects representing products with
              quantity less than the threshold
            - threshold: The threshold value used for the report
            
    Note:
        Each LowStockItem includes product_public_id, product_name,
        current_quantity, and category_name.
    """
    items = await InventoryItem.filter(quantity__lt=threshold, deleted_at__isnull=True).prefetch_related('category').all()
    response_items = [
        LowStockItem(
            product_public_id=item.public_id, product_name=item.name,
            current_quantity=item.quantity, category_name=item.category.name if item.category else None
        ) for item in items
    ]
    return LowStockItemsResponse(low_stock_items=response_items, threshold=threshold)

async def generate_most_stocked_items_report(limit: int) -> MostStockedItemsResponse:
    """
    Generates a report of inventory items with the highest stock levels.
    
    This function identifies products that have the largest quantities in stock,
    which may indicate potential overstocking issues. It only includes active
    (non-deleted) items.
    
    Args:
        limit: The maximum number of items to include in the report
        
    Returns:
        MostStockedItemsResponse: An object containing:
            - most_stocked_items: List of MostStockedItem objects representing
              products with the highest quantities, sorted in descending order
            - limit: The maximum number of items requested
            
    Note:
        Each MostStockedItem includes product_public_id, product_name,
        current_quantity, and category_name.
    """
    items = await InventoryItem.filter(deleted_at__isnull=True).order_by('-quantity').limit(limit).prefetch_related('category').all()
    response_items = [
        MostStockedItem(
            product_public_id=item.public_id, product_name=item.name,
            current_quantity=item.quantity, category_name=item.category.name if item.category else None
        ) for item in items
    ]
    return MostStockedItemsResponse(most_stocked_items=response_items, limit=limit)

async def generate_inventory_value_report() -> InventoryValueResponse:
    """
    Generates a report of the total monetary value of current inventory.
    
    This function calculates the value of each active (non-deleted) inventory item
    by multiplying its quantity by its current price, and then provides both
    the overall total and a breakdown by item.
    
    Returns:
        InventoryValueResponse: An object containing:
            - total_inventory_value: Sum of the value of all inventory items
            - items_contributing: List of InventoryValueItem objects with detailed
              information about each item's contribution to the total value
            - item_count: Total number of inventory items included in the report
            
    Note:
        Each InventoryValueItem includes product_public_id, product_name,
        current_quantity, current_price, and total_value (quantity * price).
        If an item has no current_price set, 0.0 is used as a default.
    """
    inventory_items = await InventoryItem.filter(deleted_at__isnull=True).all()
    total_value = 0.0
    value_items_breakdown = []
    for item in inventory_items:
        current_price = getattr(item, 'current_price', 0.0) # Safely access current_price
        item_total_value = item.quantity * current_price
        total_value += item_total_value
        value_items_breakdown.append(
            InventoryValueItem(
                product_public_id=item.public_id, product_name=item.name,
                current_quantity=item.quantity, current_price=current_price, total_value=item_total_value
            )
        )
    return InventoryValueResponse(
        total_inventory_value=total_value, items_contributing=value_items_breakdown, item_count=len(inventory_items)
    )
