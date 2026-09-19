"""API routes for order management using command handlers."""

from typing import Annotated
from fastapi import APIRouter, Depends, Query, status

from ..auth.models import User as AuthUser
from ..auth.security import get_current_active_admin_user, get_current_active_user
from .commands import (
    CancelOrderCommand,
    CancelOrderCommandHandler,
    CreateOrderCommand,
    CreateOrderCommandHandler,
    GetOrderCommand,
    GetOrderCommandHandler,
    ListOrdersCommand,
    ListOrdersCommandHandler,
    ShipOrderCommand,
    ShipOrderCommandHandler,
)
from .schemas import (
    OrderCancelRequestSchema,
    OrderCreateSchema,
    OrderPublicSchema,
    OrderShipRequestSchema,
    PaginatedOrderResponse,
)

router = APIRouter(
    prefix="/orders",
    tags=["Orders"],
)


@router.post("/", response_model=OrderPublicSchema, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_data: OrderCreateSchema,
    current_user: Annotated[AuthUser, Depends(get_current_active_user)],
    handler: Annotated[CreateOrderCommandHandler, Depends()],
):
    """Creates a new order.

    Requires an authenticated user.
    """
    command = CreateOrderCommand(order_data=order_data, current_user=current_user)
    return await handler(command)


@router.get("/", response_model=PaginatedOrderResponse)
async def list_orders(
    current_user: Annotated[AuthUser, Depends(get_current_active_user)],
    handler: Annotated[ListOrdersCommandHandler, Depends()],
    limit: int = Query(10, ge=1, le=100, description="Number of items per page"),
    cursor: str | None = Query(None, description="Forward cursor for pagination"),
    prev_cursor: str | None = Query(None, description="Backward cursor for pagination"),
    statuses: list[str] | None = Query(None),
):
    """Lists orders for the current user using cursor-based pagination.

    Admins can see all orders.
    """
    command = ListOrdersCommand(
        current_user=current_user,
        limit=limit,
        cursor=cursor,
        prev_cursor=prev_cursor,
        statuses=statuses,
    )
    return await handler(command)


@router.get("/{order_public_id}", response_model=OrderPublicSchema)
async def get_order(
    order_public_id: str,
    current_user: Annotated[AuthUser, Depends(get_current_active_user)],
    handler: Annotated[GetOrderCommandHandler, Depends()],
):
    """Retrieves a single order by its public ID."""
    command = GetOrderCommand(
        order_public_id=order_public_id, current_user=current_user
    )
    return await handler(command)


@router.patch("/{order_public_id}/ship", response_model=OrderPublicSchema)
async def ship_order(
    order_public_id: str,
    current_admin: Annotated[AuthUser, Depends(get_current_active_admin_user)],
    handler: Annotated[ShipOrderCommandHandler, Depends()],
    ship_data: OrderShipRequestSchema | None = None,
):
    """Marks an order as shipped.

    Requires admin privileges.
    """
    command = ShipOrderCommand(order_public_id=order_public_id, ship_data=ship_data)
    return await handler(command)


@router.patch("/{order_public_id}/cancel", response_model=OrderPublicSchema)
async def cancel_order(
    order_public_id: str,
    current_admin: Annotated[AuthUser, Depends(get_current_active_admin_user)],
    handler: Annotated[CancelOrderCommandHandler, Depends()],
    cancel_data: OrderCancelRequestSchema | None = None,
):
    """Cancels an order.

    Requires admin privileges.
    """
    command = CancelOrderCommand(
        order_public_id=order_public_id, cancel_data=cancel_data
    )
    return await handler(command)
