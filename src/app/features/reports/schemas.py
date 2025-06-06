"""Financial and Inventory Reports API Schemas

This module defines Pydantic models used for various financial and inventory
reporting endpoints in the API. It includes schemas for:

1. Total Sales Reports
2. Sales by Product
3. Sales by Category
4. Order Status Breakdowns
5. Low Stock Item Reports
6. Most Stocked Item Reports
7. Inventory Value Calculations

Each schema contains appropriate fields for request parameters and response data
with proper typing and field descriptions where applicable."""
from pydantic import BaseModel, Field
from typing import List, Optional
import datetime

# Helper schema for common time period queries
class TimePeriodQuery(BaseModel):
    start_date: Optional[datetime.date] = Field(None, description="Start date for the report period (YYYY-MM-DD)")
    end_date: Optional[datetime.date] = Field(None, description="End date for the report period (YYYY-MM-DD)")

# 1. Total Sales Over Time
class TotalSalesResponse(BaseModel):
    total_revenue: float
    item_count: int
    order_count: int
    start_date: Optional[datetime.date] = None
    end_date: Optional[datetime.date] = None

# 2. Sales by Product
class ProductSaleInfo(BaseModel):
    product_public_id: str
    product_name: str
    total_quantity_sold: int
    total_revenue: float

class SalesByProductResponse(BaseModel):
    products: List[ProductSaleInfo]
    start_date: Optional[datetime.date] = None
    end_date: Optional[datetime.date] = None

# 3. Sales by Category
class CategorySaleInfo(BaseModel):
    category_public_id: str
    category_name: str
    total_quantity_sold: int
    total_revenue: float

class SalesByCategoryResponse(BaseModel):
    categories: List[CategorySaleInfo]
    start_date: Optional[datetime.date] = None
    end_date: Optional[datetime.date] = None

# 4. Order Status Breakdown
class OrderStatusCount(BaseModel):
    status: str
    count: int

class OrderStatusBreakdownResponse(BaseModel):
    status_breakdown: List[OrderStatusCount]

# 5. Low Stock Items
class LowStockItem(BaseModel):
    product_public_id: str
    product_name: str
    current_quantity: int
    category_name: Optional[str] = None

class LowStockItemsResponse(BaseModel):
    low_stock_items: List[LowStockItem]
    threshold: int

# 6. Most Stocked Items
class MostStockedItem(BaseModel):
    product_public_id: str
    product_name: str
    current_quantity: int
    category_name: Optional[str] = None

class MostStockedItemsResponse(BaseModel):
    most_stocked_items: List[MostStockedItem]
    limit: int

# 7. Inventory Value
class InventoryValueItem(BaseModel):
    product_public_id: str
    product_name: str
    current_quantity: int
    current_price: float
    total_value: float

class InventoryValueResponse(BaseModel):
    total_inventory_value: float
    items_contributing: List[InventoryValueItem]
    item_count: int
