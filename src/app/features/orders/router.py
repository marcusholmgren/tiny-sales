from fastapi import (
    APIRouter,
    Depends,
    status,
    Query,
)
from typing import List, Optional, Annotated

from ..auth.models import User as AuthUser

from .schemas import (
    OrderCreateSchema,
    OrderPublicSchema,
    OrderShipRequestSchema,
    OrderCancelRequestSchema,
    PaginatedOrderResponse,
)

from .service import (
    _to_order_public_schema,
    create_new_order,
    get_all_orders,
    get_order_by_public_id,
    ship_existing_order,
    cancel_existing_order,
)

from ..auth.security import get_current_active_user, get_current_active_admin_user

router = APIRouter(
    prefix="/orders",
    tags=["Orders"],
)


@router.post("/", response_model=OrderPublicSchema, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_data: OrderCreateSchema,
    current_user: Annotated[AuthUser, Depends(get_current_active_user)],
):
    """
    Creates a new order.

    Requires an authenticated user.
    """
    new_order = await create_new_order(order_data, current_user)
    return await _to_order_public_schema(new_order)


@router.get("/", response_model=PaginatedOrderResponse)
async def list_orders(
    current_user: Annotated[AuthUser, Depends(get_current_active_user)],
    limit: int = Query(10, ge=1, le=100, description="Number of items per page"),
    cursor: Optional[str] = Query(None, description="Forward cursor for pagination"),
    prev_cursor: Optional[str] = Query(
        None, description="Backward cursor for pagination"
    ),
    statuses: Optional[List[str]] = Query(None),
):
    """
    Lists orders for the current user using cursor-based pagination.

    Admins can see all orders.
    """
    return await get_all_orders(
        current_user=current_user,
        limit=limit,
        cursor=cursor,
        prev_cursor=prev_cursor,
        statuses=statuses,
    )


@router.get("/{order_public_id}", response_model=OrderPublicSchema)
async def get_order(
    order_public_id: str,
    current_user: Annotated[AuthUser, Depends(get_current_active_user)],
):
    """
    Retrieves a single order by its public ID.
    """
    order = await get_order_by_public_id(order_public_id, current_user)
    return await _to_order_public_schema(order)


@router.patch("/{order_public_id}/ship", response_model=OrderPublicSchema)
async def ship_order(
    order_public_id: str,
    current_admin: Annotated[AuthUser, Depends(get_current_active_admin_user)],
    ship_data: Optional[OrderShipRequestSchema] = None,
):
    """
    Marks an order as shipped.

    Requires admin privileges.
    """
    shipped_order = await ship_existing_order(order_public_id, ship_data)
    return await _to_order_public_schema(shipped_order)


@router.patch("/{order_public_id}/cancel", response_model=OrderPublicSchema)
async def cancel_order(
    order_public_id: str,
    current_admin: Annotated[AuthUser, Depends(get_current_active_admin_user)],
    cancel_data: Optional[OrderCancelRequestSchema] = None,
):
    """
    Cancels an order.

    Requires admin privileges.
    """
    cancelled_order = await cancel_existing_order(order_public_id, cancel_data)
    return await _to_order_public_schema(cancelled_order)
