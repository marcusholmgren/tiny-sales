"""Command objects and handlers for report generation operations."""

import datetime
from dataclasses import dataclass

from ...common import BaseCommand, CommandHandler
from ..auth.models import User as AuthUser
from . import schemas, service


@dataclass(frozen=True, slots=True)
class GetTotalSalesReportCommand(BaseCommand):
    """Command payload for generating total sales report."""

    current_user: AuthUser
    start_date: datetime.date | None = None
    end_date: datetime.date | None = None


class GetTotalSalesReportCommandHandler(
    CommandHandler[GetTotalSalesReportCommand, schemas.TotalSalesResponse]
):
    """Command handler for total sales report generation."""

    async def execute(
        self, command: GetTotalSalesReportCommand
    ) -> schemas.TotalSalesResponse:
        """Executes total sales report generation.

        Args:
            command: The command containing filtering date range and user context.

        Returns:
            TotalSalesResponse: The generated report response schema.
        """
        return await service.generate_total_sales_report(
            current_user=command.current_user,
            start_date=command.start_date,
            end_date=command.end_date,
        )


@dataclass(frozen=True, slots=True)
class GetSalesByProductReportCommand(BaseCommand):
    """Command payload for generating sales by product report."""

    current_user: AuthUser
    start_date: datetime.date | None = None
    end_date: datetime.date | None = None


class GetSalesByProductReportCommandHandler(
    CommandHandler[GetSalesByProductReportCommand, schemas.SalesByProductResponse]
):
    """Command handler for sales by product report generation."""

    async def execute(
        self, command: GetSalesByProductReportCommand
    ) -> schemas.SalesByProductResponse:
        """Executes sales by product report generation.

        Args:
            command: The command containing filtering date range and user context.

        Returns:
            SalesByProductResponse: The generated report response schema.
        """
        return await service.generate_sales_by_product_report(
            current_user=command.current_user,
            start_date=command.start_date,
            end_date=command.end_date,
        )


@dataclass(frozen=True, slots=True)
class GetSalesByCategoryReportCommand(BaseCommand):
    """Command payload for generating sales by category report."""

    current_user: AuthUser
    start_date: datetime.date | None = None
    end_date: datetime.date | None = None


class GetSalesByCategoryReportCommandHandler(
    CommandHandler[GetSalesByCategoryReportCommand, schemas.SalesByCategoryResponse]
):
    """Command handler for sales by category report generation."""

    async def execute(
        self, command: GetSalesByCategoryReportCommand
    ) -> schemas.SalesByCategoryResponse:
        """Executes sales by category report generation.

        Args:
            command: The command containing filtering date range and user context.

        Returns:
            SalesByCategoryResponse: The generated report response schema.
        """
        return await service.generate_sales_by_category_report(
            current_user=command.current_user,
            start_date=command.start_date,
            end_date=command.end_date,
        )


@dataclass(frozen=True, slots=True)
class GetOrderStatusBreakdownReportCommand(BaseCommand):
    """Command payload for generating order status breakdown report."""

    current_user: AuthUser


class GetOrderStatusBreakdownReportCommandHandler(
    CommandHandler[
        GetOrderStatusBreakdownReportCommand, schemas.OrderStatusBreakdownResponse
    ]
):
    """Command handler for order status breakdown report generation."""

    async def execute(
        self, command: GetOrderStatusBreakdownReportCommand
    ) -> schemas.OrderStatusBreakdownResponse:
        """Executes order status breakdown report generation.

        Args:
            command: The command containing user context.

        Returns:
            OrderStatusBreakdownResponse: The generated report response schema.
        """
        return await service.generate_order_status_breakdown_report(
            current_user=command.current_user
        )


@dataclass(frozen=True, slots=True)
class GetLowStockItemsReportCommand(BaseCommand):
    """Command payload for generating low stock items report."""

    threshold: int = 10


class GetLowStockItemsReportCommandHandler(
    CommandHandler[GetLowStockItemsReportCommand, schemas.LowStockItemsResponse]
):
    """Command handler for low stock items report generation."""

    async def execute(
        self, command: GetLowStockItemsReportCommand
    ) -> schemas.LowStockItemsResponse:
        """Executes low stock items report generation.

        Args:
            command: The command containing quantity threshold.

        Returns:
            LowStockItemsResponse: The generated report response schema.
        """
        return await service.generate_low_stock_items_report(
            threshold=command.threshold
        )


@dataclass(frozen=True, slots=True)
class GetMostStockedItemsReportCommand(BaseCommand):
    """Command payload for generating most stocked items report."""

    limit: int = 10


class GetMostStockedItemsReportCommandHandler(
    CommandHandler[GetMostStockedItemsReportCommand, schemas.MostStockedItemsResponse]
):
    """Command handler for most stocked items report generation."""

    async def execute(
        self, command: GetMostStockedItemsReportCommand
    ) -> schemas.MostStockedItemsResponse:
        """Executes most stocked items report generation.

        Args:
            command: The command containing result limit count.

        Returns:
            MostStockedItemsResponse: The generated report response schema.
        """
        return await service.generate_most_stocked_items_report(limit=command.limit)


@dataclass(frozen=True, slots=True)
class GetInventoryValueReportCommand(BaseCommand):
    """Command payload for generating inventory total value report."""

    pass


class GetInventoryValueReportCommandHandler(
    CommandHandler[GetInventoryValueReportCommand, schemas.InventoryValueResponse]
):
    """Command handler for inventory value report generation."""

    async def execute(
        self, command: GetInventoryValueReportCommand
    ) -> schemas.InventoryValueResponse:
        """Executes inventory total monetary value report generation.

        Args:
            command: The GetInventoryValueReportCommand instance.

        Returns:
            InventoryValueResponse: The generated report response schema.
        """
        return await service.generate_inventory_value_report()
