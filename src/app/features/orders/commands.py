"""Command objects and handlers for order management operations."""

from dataclasses import dataclass

from ...common import BaseCommand, CommandHandler
from ..auth.models import User as AuthUser
from . import schemas, service


@dataclass(frozen=True, slots=True)
class CreateOrderCommand(BaseCommand):
    """Command payload for creating a new order."""

    order_data: schemas.OrderCreateSchema
    current_user: AuthUser


class CreateOrderCommandHandler(
    CommandHandler[CreateOrderCommand, schemas.OrderPublicSchema]
):
    """Command handler for placing a new order."""

    async def execute(self, command: CreateOrderCommand) -> schemas.OrderPublicSchema:
        """Executes order creation and transforms result to OrderPublicSchema.

        Args:
            command: The command containing order details and current user.

        Returns:
            OrderPublicSchema: Public order schema representation.
        """
        new_order = await service.create_new_order(
            command.order_data, command.current_user
        )
        return await service._to_order_public_schema(new_order)


@dataclass(frozen=True, slots=True)
class ListOrdersCommand(BaseCommand):
    """Command payload for listing user or all orders with pagination."""

    current_user: AuthUser
    limit: int = 10
    cursor: str | None = None
    prev_cursor: str | None = None
    statuses: list[str] | None = None


class ListOrdersCommandHandler(
    CommandHandler[ListOrdersCommand, schemas.PaginatedOrderResponse]
):
    """Command handler for listing orders."""

    async def execute(
        self, command: ListOrdersCommand
    ) -> schemas.PaginatedOrderResponse:
        """Executes paginated order retrieval.

        Args:
            command: The command containing filters, limits, cursors, and current user.

        Returns:
            PaginatedOrderResponse: Paginated order response schema.
        """
        return await service.get_all_orders(
            current_user=command.current_user,
            limit=command.limit,
            cursor=command.cursor,
            prev_cursor=command.prev_cursor,
            statuses=command.statuses,
        )


@dataclass(frozen=True, slots=True)
class GetOrderCommand(BaseCommand):
    """Command payload for retrieving a specific order."""

    order_public_id: str
    current_user: AuthUser


class GetOrderCommandHandler(
    CommandHandler[GetOrderCommand, schemas.OrderPublicSchema]
):
    """Command handler for retrieving a single order."""

    async def execute(self, command: GetOrderCommand) -> schemas.OrderPublicSchema:
        """Executes single order retrieval.

        Args:
            command: The command containing order_public_id and current user.

        Returns:
            OrderPublicSchema: The order details schema.
        """
        order = await service.get_order_by_public_id(
            command.order_public_id, command.current_user
        )
        return await service._to_order_public_schema(order)


@dataclass(frozen=True, slots=True)
class ShipOrderCommand(BaseCommand):
    """Command payload for marking an order as shipped."""

    order_public_id: str
    ship_data: schemas.OrderShipRequestSchema | None = None


class ShipOrderCommandHandler(
    CommandHandler[ShipOrderCommand, schemas.OrderPublicSchema]
):
    """Command handler for shipping an existing order."""

    async def execute(self, command: ShipOrderCommand) -> schemas.OrderPublicSchema:
        """Executes shipping transition on an order.

        Args:
            command: The command containing public ID and shipping metadata.

        Returns:
            OrderPublicSchema: Updated order details schema.
        """
        shipped_order = await service.ship_existing_order(
            command.order_public_id, command.ship_data
        )
        return await service._to_order_public_schema(shipped_order)


@dataclass(frozen=True, slots=True)
class CancelOrderCommand(BaseCommand):
    """Command payload for cancelling an existing order."""

    order_public_id: str
    cancel_data: schemas.OrderCancelRequestSchema | None = None


class CancelOrderCommandHandler(
    CommandHandler[CancelOrderCommand, schemas.OrderPublicSchema]
):
    """Command handler for cancelling an existing order."""

    async def execute(self, command: CancelOrderCommand) -> schemas.OrderPublicSchema:
        """Executes cancellation transition on an order.

        Args:
            command: The command containing public ID and cancellation metadata.

        Returns:
            OrderPublicSchema: Updated order details schema.
        """
        cancelled_order = await service.cancel_existing_order(
            command.order_public_id, command.cancel_data
        )
        return await service._to_order_public_schema(cancelled_order)
