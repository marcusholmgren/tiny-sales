import logging
from fastapi import APIRouter, Depends, Query
from typing import Annotated # Annotated was missing in original provided file for current_user

# Auth dependencies and User model
from ..auth.models import User as AuthUser # Use AuthUser alias
from ..auth.security import get_current_active_user, get_current_active_admin_user

# Schemas for request (TimePeriodQuery) and responses
from .schemas import (
    TimePeriodQuery, TotalSalesResponse, SalesByProductResponse,
    SalesByCategoryResponse, OrderStatusBreakdownResponse, LowStockItemsResponse,
    MostStockedItemsResponse, InventoryValueResponse
)
# Service functions that contain the business logic
from . import service as report_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/reports",
    tags=["Reports"],
    # Apply auth dependency to all routes in this router
    dependencies=[Depends(get_current_active_user)],
    responses={404: {"description": "Not found"}}, # General 404 for this router
)

@router.get("/sales/total", response_model=TotalSalesResponse)
async def get_total_sales_report(
    current_user: Annotated[AuthUser, Depends(get_current_active_user)], # Use AuthUser
    period: TimePeriodQuery = Depends() # Injects query params from TimePeriodQuery
):
    return await report_service.generate_total_sales_report(
        current_user=current_user, start_date=period.start_date, end_date=period.end_date
    )

@router.get("/sales/by-product", response_model=SalesByProductResponse)
async def get_sales_by_product_report(
    current_user: Annotated[AuthUser, Depends(get_current_active_user)], # Use AuthUser
    period: TimePeriodQuery = Depends()
):
    return await report_service.generate_sales_by_product_report(
        current_user=current_user, start_date=period.start_date, end_date=period.end_date
    )

@router.get("/sales/by-category", response_model=SalesByCategoryResponse)
async def get_sales_by_category_report(
    current_user: Annotated[AuthUser, Depends(get_current_active_user)], # Use AuthUser
    period: TimePeriodQuery = Depends()
):
    return await report_service.generate_sales_by_category_report(
        current_user=current_user, start_date=period.start_date, end_date=period.end_date
    )

@router.get("/orders/status-breakdown", response_model=OrderStatusBreakdownResponse)
async def get_order_status_breakdown_report(
    current_user: Annotated[AuthUser, Depends(get_current_active_user)] # Use AuthUser
):
    return await report_service.generate_order_status_breakdown_report(current_user=current_user)

# Inventory reports typically require admin privileges
@router.get("/inventory/low-stock", response_model=LowStockItemsResponse)
async def get_low_stock_items_report(
    current_admin: Annotated[AuthUser, Depends(get_current_active_admin_user)], # Use AuthUser and admin dep
    threshold: int = Query(10, ge=0, description="Stock quantity threshold")
):
    return await report_service.generate_low_stock_items_report(threshold=threshold)

@router.get("/inventory/most-stocked", response_model=MostStockedItemsResponse)
async def get_most_stocked_items_report(
    current_admin: Annotated[AuthUser, Depends(get_current_active_admin_user)], # Use AuthUser and admin dep
    limit: int = Query(10, ge=1, le=100, description="Number of items to retrieve")
):
    return await report_service.generate_most_stocked_items_report(limit=limit)

@router.get("/inventory/value", response_model=InventoryValueResponse)
async def get_inventory_value_report(
    current_admin: Annotated[AuthUser, Depends(get_current_active_admin_user)] # Use AuthUser and admin dep
):
    return await report_service.generate_inventory_value_report()
