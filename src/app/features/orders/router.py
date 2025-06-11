from fastapi import APIRouter, HTTPException, Depends, status, Query # HTTPException kept for FastAPI direct use
from typing import List, Optional, Annotated

# Models from this feature and related features
# from .models import Order # No longer directly used in router
from ..auth.models import User as AuthUser # User model for auth

# Schemas from this feature and related features
from .schemas import (
    OrderCreateSchema, OrderPublicSchema,
    # OrderItemPublicSchema, OrderEventPublicSchema, # Moved to service.py
    OrderShipRequestSchema, OrderCancelRequestSchema
)
# from ..auth.schemas import UserResponse # Moved to service.py

# Service imports
from .service import (
    _to_order_public_schema, create_new_order, get_all_orders,
    get_order_by_public_id, ship_existing_order, cancel_existing_order
)

# Auth dependencies
from ..auth.security import get_current_active_user, get_current_active_admin_user

# Utilities
# (generate_ksuid moved to service layer)

# logger = logging.getLogger(__name__) # Not used

router = APIRouter(
    prefix="/orders",
    tags=["Orders"],
)

@router.post("/", response_model=OrderPublicSchema, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_data: OrderCreateSchema,
    current_user: Annotated[AuthUser, Depends(get_current_active_user)]
):
    # The core order creation logic is now in the service layer
    new_order = await create_new_order(order_data, current_user)

    # Convert the Order model instance to an OrderPublicSchema for the response
    return await _to_order_public_schema(new_order)


@router.get("/", response_model=List[OrderPublicSchema])
async def list_orders(
    current_user: Annotated[AuthUser, Depends(get_current_active_user)],
    page: int = Query(1, ge=1), size: int = Query(10, ge=1, le=100),
    statuses: Optional[List[str]] = Query(None)
):
    orders_list = await get_all_orders(current_user, page, size, statuses)
    return [await _to_order_public_schema(order) for order in orders_list]

@router.get("/{order_public_id}", response_model=OrderPublicSchema)
async def get_order(
    order_public_id: str,
    current_user: Annotated[AuthUser, Depends(get_current_active_user)]
):
    order = await get_order_by_public_id(order_public_id, current_user)
    return await _to_order_public_schema(order)

@router.patch("/{order_public_id}/ship", response_model=OrderPublicSchema)
async def ship_order(
    order_public_id: str,
    current_admin: Annotated[AuthUser, Depends(get_current_active_admin_user)], # AuthZ handled by Depends
    ship_data: Optional[OrderShipRequestSchema] = None
):
    shipped_order = await ship_existing_order(order_public_id, ship_data)
    return await _to_order_public_schema(shipped_order)

@router.patch("/{order_public_id}/cancel", response_model=OrderPublicSchema)
async def cancel_order(
    order_public_id: str,
    current_admin: Annotated[AuthUser, Depends(get_current_active_admin_user)], # AuthZ handled by Depends
    cancel_data: Optional[OrderCancelRequestSchema] = None
):
    cancelled_order = await cancel_existing_order(order_public_id, cancel_data)
    return await _to_order_public_schema(cancelled_order)
