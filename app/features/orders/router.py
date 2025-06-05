import logging
from fastapi import APIRouter, HTTPException, Depends, status, Query
from tortoise.transactions import in_transaction
from tortoise.exceptions import DoesNotExist
from typing import List, Optional, Annotated

# Models from this feature and related features
from .models import Order, OrderItem, OrderEvent # Local models
from app.features.inventory.models import InventoryItem # Related model
from app.features.auth.models import User as AuthUser # User model for auth

# Schemas from this feature and related features
from .schemas import (
    OrderCreateSchema, OrderPublicSchema,
    OrderItemPublicSchema, OrderEventPublicSchema, # Removed OrderItemCreateSchema as it's input only
    OrderShipRequestSchema, OrderCancelRequestSchema
)
from app.features.auth.schemas import UserResponse # For embedding in OrderPublicSchema

# Auth dependencies
from app.features.auth.security import get_current_active_user, get_current_active_admin_user

# Utilities
from app.common.models import generate_ksuid # KSUID generation

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/orders",
    tags=["Orders"],
)

async def _to_order_public_schema(order: Order) -> OrderPublicSchema:
    # Ensure related fields are prefetched before calling this
    user_resp = UserResponse.model_validate(order.user) if order.user and hasattr(order, 'user') else None

    items_resp = []
    if hasattr(order, 'items'): # Check if items relation is loaded
        for item_model in await order.items.all().select_related('item'): # Ensure item (InventoryItem) is loaded
            inventory_item_model = item_model.item # This is the InventoryItem instance
            items_resp.append(OrderItemPublicSchema(
                public_id=item_model.public_id,
                product_public_id=inventory_item_model.public_id, # Get public_id from related InventoryItem
                quantity=item_model.quantity,
                price_at_purchase=item_model.price_at_purchase,
                # product_name=inventory_item_model.name # Example: if you want to add product name
            ))

    events_resp = []
    if hasattr(order, 'events'): # Check if events relation is loaded
      events_resp = [OrderEventPublicSchema.model_validate(e) for e in await order.events.all()]

    return OrderPublicSchema(
        public_id=order.public_id,
        order_id=order.order_id,
        contact_name=order.contact_name,
        contact_email=order.contact_email,
        delivery_address=order.delivery_address,
        status=order.status,
        user=user_resp,
        items=items_resp,
        events=events_resp,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )

@router.post("/", response_model=OrderPublicSchema, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_data: OrderCreateSchema,
    current_user: Annotated[AuthUser, Depends(get_current_active_user)]
):
    async with in_transaction() as conn:
        new_order_id_str = await Order.generate_next_order_id()
        order = await Order.create(
            public_id=generate_ksuid(), order_id=new_order_id_str,
            contact_name=order_data.contact_name, contact_email=order_data.contact_email,
            delivery_address=order_data.delivery_address, status="placed",
            user=current_user, using_db=conn
        )
        for item_data in order_data.items:
            inventory_item = await InventoryItem.get_or_none(
                public_id=item_data.product_public_id, using_db=conn
            ).select_for_update()
            if not inventory_item:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Item {item_data.product_public_id} not found.")
            if inventory_item.quantity < item_data.quantity:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Not enough stock for {inventory_item.name}.")

            inventory_item.quantity -= item_data.quantity
            await inventory_item.save(using_db=conn, update_fields=['quantity'])
            await OrderItem.create(
                public_id=generate_ksuid(), order=order, item_id=inventory_item.id,
                quantity=item_data.quantity, price_at_purchase=item_data.price_at_purchase,
                using_db=conn
            )
        await OrderEvent.create(
            public_id=generate_ksuid(), order=order, event_type="order_placed",
            data={"message": "Order created successfully."}, using_db=conn
        )
        # No explicit commit needed, transaction context manager handles it.

    # Fetch the full order with relations for response after transaction commits
    full_order = await Order.get(id=order.id).prefetch_related("user", "items__item", "events")
    return await _to_order_public_schema(full_order)


@router.get("/", response_model=List[OrderPublicSchema])
async def list_orders(
    current_user: Annotated[AuthUser, Depends(get_current_active_user)],
    page: int = Query(1, ge=1), size: int = Query(10, ge=1, le=100)
):
    offset = (page - 1) * size
    query = Order.all().prefetch_related("user", "items__item", "events").order_by("-created_at")
    if current_user.role != "admin":
        query = query.filter(user_id=current_user.id)
    orders = await query.offset(offset).limit(size)
    return [await _to_order_public_schema(order) for order in orders]

@router.get("/{order_public_id}", response_model=OrderPublicSchema)
async def get_order(
    order_public_id: str,
    current_user: Annotated[AuthUser, Depends(get_current_active_user)]
):
    try:
        order = await Order.get(public_id=order_public_id).prefetch_related("user", "items__item", "events")
    except DoesNotExist:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Order {order_public_id} not found.")
    if current_user.role != "admin" and order.user_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized.")
    return await _to_order_public_schema(order)

@router.patch("/{order_public_id}/ship", response_model=OrderPublicSchema)
async def ship_order(
    order_public_id: str,
    current_admin: Annotated[AuthUser, Depends(get_current_active_admin_user)],
    ship_data: Optional[OrderShipRequestSchema] = None
):
    order = await Order.get_or_none(public_id=order_public_id) # No prefetch needed yet
    if not order: raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found.")
    if order.status in ["shipped", "cancelled"]:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Order is already {order.status}.")

    async with in_transaction() as conn:
        order_locked = await Order.get(id=order.id, using_db=conn).select_for_update()
        order_locked.status = "shipped"
        await order_locked.save(using_db=conn, update_fields=['status'])
        event_data = ship_data.model_dump(exclude_none=True) if ship_data else {}
        if not event_data: event_data = {"message": "Order marked as shipped."}
        await OrderEvent.create(
            public_id=generate_ksuid(), order=order_locked, event_type="order_shipped",
            data=event_data, using_db=conn
        )
    full_order = await Order.get(id=order.id).prefetch_related("user", "items__item", "events")
    return await _to_order_public_schema(full_order)

@router.patch("/{order_public_id}/cancel", response_model=OrderPublicSchema)
async def cancel_order(
    order_public_id: str,
    current_admin: Annotated[AuthUser, Depends(get_current_active_admin_user)],
    cancel_data: Optional[OrderCancelRequestSchema] = None
):
    order = await Order.get_or_none(public_id=order_public_id) # No prefetch needed yet
    if not order: raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found.")
    if order.status == "cancelled":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Order already cancelled.")
    if order.status == "shipped" and not (cancel_data and cancel_data.reason):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Shipped order cancellation requires reason.")

    should_replenish = order.status not in ["delivered", "shipped"] # Example: don't replenish if shipped or delivered. Adjust as needed.

    async with in_transaction() as conn:
        order_locked = await Order.get(id=order.id, using_db=conn).select_for_update()
        order_locked.status = "cancelled"
        await order_locked.save(using_db=conn, update_fields=['status'])

        if should_replenish:
            order_items_for_replenish = await OrderItem.filter(order_id=order_locked.id).select_related("item").using_db(conn)
            for oi in order_items_for_replenish:
                inv_item = await InventoryItem.get(id=oi.item_id, using_db=conn).select_for_update() # Lock inv item
                inv_item.quantity += oi.quantity
                await inv_item.save(using_db=conn, update_fields=['quantity'])

        event_data = cancel_data.model_dump(exclude_none=True) if cancel_data else {}
        event_data["stock_replenished"] = should_replenish
        if not cancel_data or not cancel_data.reason : event_data.setdefault("message", "Order cancelled.")

        await OrderEvent.create(
            public_id=generate_ksuid(), order=order_locked, event_type="order_cancelled",
            data=event_data, using_db=conn
        )
    full_order = await Order.get(id=order.id).prefetch_related("user", "items__item", "events")
    return await _to_order_public_schema(full_order)
