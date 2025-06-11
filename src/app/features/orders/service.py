# External dependencies
from tortoise.transactions import in_transaction
from tortoise.exceptions import DoesNotExist
from fastapi import HTTPException, status # For exceptions, status codes

# Typing
from typing import List, Optional

# Models from this feature and related features
from .models import Order, OrderItem, OrderEvent # Local models
from ..inventory.models import InventoryItem # Related model
from ..auth.models import User as AuthUser # User model for auth

# Schemas from this feature and related features
from .schemas import (
    OrderPublicSchema, OrderItemPublicSchema, OrderEventPublicSchema, OrderCreateSchema,
    OrderShipRequestSchema, OrderCancelRequestSchema
)
from ..auth.schemas import UserResponse # For embedding in OrderPublicSchema

# Utilities
from ...common.models import generate_ksuid # KSUID generation


async def get_order_by_public_id(order_public_id: str, current_user: AuthUser) -> Order:
    try:
        # Prefetch related fields that are likely to be used, e.g., in _to_order_public_schema
        order = await Order.get(public_id=order_public_id).prefetch_related("user", "items__item", "events")
    except DoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Order {order_public_id} not found.")

    # Authorization check: Admin can see any order, regular users only their own.
    if current_user.role != "admin" and order.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this order.")

    return order

async def get_all_orders(current_user: AuthUser, page: int, size: int, statuses: Optional[List[str]]) -> List[Order]:
    offset = (page - 1) * size
    # Base query with prefetching for efficiency, ordered by creation date descending
    query = Order.all().prefetch_related("user", "items__item", "events").order_by("-created_at")

    if statuses:
        # Process statuses: remove whitespace and filter out empty strings
        processed_statuses = [s.strip() for s in statuses if s.strip()]
        if processed_statuses:
            query = query.filter(status__in=processed_statuses)

    # Non-admin users can only see their own orders
    if current_user.role != "admin":
        query = query.filter(user_id=current_user.id)

    orders = await query.offset(offset).limit(size)
    return orders

async def create_new_order(order_data: OrderCreateSchema, current_user: AuthUser) -> Order:
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
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Item {item_data.product_public_id} not found.")
            if inventory_item.quantity < item_data.quantity:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Not enough stock for {inventory_item.name}.")

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
    # This is important to ensure all related data (user, items, events) is loaded
    # before it's passed to _to_order_public_schema or used otherwise.
    full_order = await Order.get(id=order.id).prefetch_related("user", "items__item", "events")
    return full_order


async def ship_existing_order(order_public_id: str, ship_data: Optional[OrderShipRequestSchema]) -> Order:
    order = await Order.get_or_none(public_id=order_public_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
    if order.status in ["shipped", "cancelled"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Order is already {order.status}.")

    async with in_transaction() as conn:
        # Lock the order row for update
        order_locked = await Order.get(id=order.id, using_db=conn).select_for_update()

        order_locked.status = "shipped"
        await order_locked.save(using_db=conn, update_fields=['status'])

        event_data = ship_data.model_dump(exclude_none=True) if ship_data else {}
        if not event_data:  # Ensure there's always a message
            event_data = {"message": "Order marked as shipped."}

        await OrderEvent.create(
            public_id=generate_ksuid(),
            order=order_locked,
            event_type="order_shipped",
            data=event_data,
            using_db=conn
        )
        # Transaction is committed automatically upon exiting the 'async with' block

    # Fetch the full order with all relations to return a complete view
    full_order_after_ship = await Order.get(id=order.id).prefetch_related("user", "items__item", "events")
    return full_order_after_ship


async def cancel_existing_order(order_public_id: str, cancel_data: Optional[OrderCancelRequestSchema]) -> Order:
    order = await Order.get_or_none(public_id=order_public_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
    if order.status == "cancelled":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order already cancelled.")
    if order.status == "shipped" and not (cancel_data and cancel_data.reason):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Shipped order cancellation requires a reason.")

    # Determine if stock should be replenished based on current order status
    # Example: Do not replenish if already delivered or if it was shipped and policy dictates no return to stock for shipped items.
    # This logic can be adjusted based on specific business rules.
    should_replenish = order.status not in ["delivered", "shipped"]

    async with in_transaction() as conn:
        order_locked = await Order.get(id=order.id, using_db=conn).select_for_update()

        order_locked.status = "cancelled"
        await order_locked.save(using_db=conn, update_fields=['status'])

        if should_replenish:
            # Fetch order items related to this order, ensuring the related inventory item is also fetched
            order_items_for_replenish = await OrderItem.filter(order_id=order_locked.id).select_related("item").using_db(conn)
            for oi in order_items_for_replenish:
                # Lock the inventory item row for update
                inv_item = await InventoryItem.get(id=oi.item_id, using_db=conn).select_for_update()
                inv_item.quantity += oi.quantity
                await inv_item.save(using_db=conn, update_fields=['quantity'])

        event_data = cancel_data.model_dump(exclude_none=True) if cancel_data else {}
        event_data["stock_replenished"] = should_replenish
        if not (cancel_data and cancel_data.reason): # Add a default message if no reason is provided
            event_data.setdefault("message", "Order cancelled.")

        await OrderEvent.create(
            public_id=generate_ksuid(),
            order=order_locked,
            event_type="order_cancelled",
            data=event_data,
            using_db=conn
        )
        # Transaction commits automatically

    # Fetch the full order details to return
    full_order_after_cancel = await Order.get(id=order.id).prefetch_related("user", "items__item", "events")
    return full_order_after_cancel

async def _to_order_public_schema(order: Order) -> OrderPublicSchema:
    # Ensure related fields are prefetched before calling this
    user_resp = UserResponse.model_validate(order.user) if order.user and hasattr(order, 'user') else None

    items_resp = []
    if hasattr(order, 'items'): # Check if items relation is loaded
        # Ensure item (InventoryItem) is loaded through select_related when order.items was fetched
        for item_model in await order.items.all(): # No need for .select_related('item') here if already prefetched
            inventory_item_model = item_model.item # This is the InventoryItem instance
            if not inventory_item_model:
                # This case should ideally not happen if data is consistent and prefetching is done correctly
                # Consider logging a warning or raising an error if appropriate
                # For now, we'll skip this item or handle as per application's error strategy
                continue # Or raise an error

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
