"""Reporting API endpoints for eCommerce analytics using command handlers."""

import logging
from typing import Annotated
from fastapi import APIRouter, Depends, Query

from ..auth.models import User as AuthUser
from ..auth.security import get_current_active_admin_user, get_current_active_user
from .commands import (
    GetInventoryValueReportCommand,
    GetInventoryValueReportCommandHandler,
    GetLowStockItemsReportCommand,
    GetLowStockItemsReportCommandHandler,
    GetMostStockedItemsReportCommand,
    GetMostStockedItemsReportCommandHandler,
    GetOrderStatusBreakdownReportCommand,
    GetOrderStatusBreakdownReportCommandHandler,
    GetSalesByCategoryReportCommand,
    GetSalesByCategoryReportCommandHandler,
    GetSalesByProductReportCommand,
    GetSalesByProductReportCommandHandler,
    GetTotalSalesReportCommand,
    GetTotalSalesReportCommandHandler,
)
from .schemas import (
    InventoryValueResponse,
    LowStockItemsResponse,
    MostStockedItemsResponse,
    OrderStatusBreakdownResponse,
    SalesByCategoryResponse,
    SalesByProductResponse,
    TimePeriodQuery,
    TotalSalesResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/reports",
    tags=["Reports"],
    dependencies=[Depends(get_current_active_user)],
    responses={404: {"description": "Not found"}},
)


@router.get("/sales/total", response_model=TotalSalesResponse)
async def get_total_sales_report(
    current_user: Annotated[AuthUser, Depends(get_current_active_user)],
    handler: Annotated[GetTotalSalesReportCommandHandler, Depends()],
    period: TimePeriodQuery = Depends(),
):
    """Retrieves total sales report."""
    command = GetTotalSalesReportCommand(
        current_user=current_user,
        start_date=period.start_date,
        end_date=period.end_date,
    )
    return await handler(command)


@router.get("/sales/by-product", response_model=SalesByProductResponse)
async def get_sales_by_product_report(
    current_user: Annotated[AuthUser, Depends(get_current_active_user)],
    handler: Annotated[GetSalesByProductReportCommandHandler, Depends()],
    period: TimePeriodQuery = Depends(),
):
    """Retrieves sales breakdown by product report."""
    command = GetSalesByProductReportCommand(
        current_user=current_user,
        start_date=period.start_date,
        end_date=period.end_date,
    )
    return await handler(command)


@router.get("/sales/by-category", response_model=SalesByCategoryResponse)
async def get_sales_by_category_report(
    current_user: Annotated[AuthUser, Depends(get_current_active_user)],
    handler: Annotated[GetSalesByCategoryReportCommandHandler, Depends()],
    period: TimePeriodQuery = Depends(),
):
    """Retrieves sales breakdown by category report."""
    command = GetSalesByCategoryReportCommand(
        current_user=current_user,
        start_date=period.start_date,
        end_date=period.end_date,
    )
    return await handler(command)


@router.get("/orders/status-breakdown", response_model=OrderStatusBreakdownResponse)
async def get_order_status_breakdown_report(
    current_user: Annotated[AuthUser, Depends(get_current_active_user)],
    handler: Annotated[GetOrderStatusBreakdownReportCommandHandler, Depends()],
):
    """Retrieves order status breakdown report."""
    command = GetOrderStatusBreakdownReportCommand(current_user=current_user)
    return await handler(command)


@router.get("/inventory/low-stock", response_model=LowStockItemsResponse)
async def get_low_stock_items_report(
    current_admin: Annotated[AuthUser, Depends(get_current_active_admin_user)],
    handler: Annotated[GetLowStockItemsReportCommandHandler, Depends()],
    threshold: int = Query(10, ge=0, description="Stock quantity threshold"),
):
    """Retrieves low stock inventory report."""
    command = GetLowStockItemsReportCommand(threshold=threshold)
    return await handler(command)


@router.get("/inventory/most-stocked", response_model=MostStockedItemsResponse)
async def get_most_stocked_items_report(
    current_admin: Annotated[AuthUser, Depends(get_current_active_admin_user)],
    handler: Annotated[GetMostStockedItemsReportCommandHandler, Depends()],
    limit: int = Query(10, ge=1, le=100, description="Number of items to retrieve"),
):
    """Retrieves most stocked inventory report."""
    command = GetMostStockedItemsReportCommand(limit=limit)
    return await handler(command)


@router.get("/inventory/value", response_model=InventoryValueResponse)
async def get_inventory_value_report(
    current_admin: Annotated[AuthUser, Depends(get_current_active_admin_user)],
    handler: Annotated[GetInventoryValueReportCommandHandler, Depends()],
):
    """Retrieves total inventory valuation report."""
    command = GetInventoryValueReportCommand()
    return await handler(command)
