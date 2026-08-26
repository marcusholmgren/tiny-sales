# External dependencies
import datetime
from tortoise.transactions import in_transaction
from tortoise.exceptions import DoesNotExist
from tortoise.expressions import Q
from fastapi import HTTPException, status  # For exceptions, status codes

# Typing
from typing import List, Optional

# Models from this feature and related features
from .models import Order, OrderItem, OrderEvent  # Local models
from ..inventory.models import InventoryItem  # Related model
from ..auth.models import User as AuthUser  # User model for auth

# Schemas from this feature and related features
from .schemas import (
    OrderPublicSchema,
    OrderItemPublicSchema,
    OrderEventPublicSchema,
    OrderCreateSchema,
    OrderShipRequestSchema,
    OrderCancelRequestSchema,
    PaginatedOrderResponse,
)
from ..auth.schemas import UserResponse  # For embedding in OrderPublicSchema

# Utilities
from ...common.models import generate_ksuid  # KSUID generation
from ...common import MoneySchema
from ...common.cursor import encode_cursor, decode_cursor


async def get_order_by_public_id(order_public_id: str, current_user: AuthUser) -> Order:
    try:
        # Prefetch related fields that are likely to be used, e.g., in _to_order_public_schema
        order = await Order.get(public_id=order_public_id).prefetch_related(
            "user", "items__item", "events"
        )
    except DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order {order_public_id} not found.",
        )

    # Authorization check: Admin can see any order, regular users only their own.
    if current_user.role != "admin" and order.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this order.",
        )

    return order


async def get_all_orders(
    current_user: AuthUser,
    limit: int = 10,
    cursor: Optional[str] = None,
    prev_cursor: Optional[str] = None,
    statuses: Optional[List[str]] = None,
) -> PaginatedOrderResponse:
    base_filter = Q()

    if statuses:
        processed_statuses = [s.strip() for s in statuses if s.strip()]
        if processed_statuses:
            base_filter &= Q(status__in=processed_statuses)

    if current_user.role != "admin":
        base_filter &= Q(user_id=current_user.id)

    if prev_cursor:
        try:
            c_created_at_iso, c_id = decode_cursor(prev_cursor)
            c_created_at = datetime.datetime.fromisoformat(c_created_at_iso)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid prev_cursor"
            )
        cursor_filter = Q(created_at__gt=c_created_at) | Q(
            created_at=c_created_at, id__gt=c_id
        )
        query_filter = base_filter & cursor_filter
        orders_db = (
            await Order.filter(query_filter)
            .prefetch_related("user", "items__item", "events")
            .order_by("created_at", "id")
            .limit(limit + 1)
        )
        has_prev = len(orders_db) > limit
        orders_db = orders_db[:limit]
        orders_db.reverse()

        if orders_db:
            first_order = orders_db[0]
            last_order = orders_db[-1]
            after_filter = base_filter & (
                Q(created_at__lt=last_order.created_at)
                | Q(created_at=last_order.created_at, id__lt=last_order.id)
            )
            has_next = await Order.filter(after_filter).exists()
            next_cursor = (
                encode_cursor([last_order.created_at.isoformat(), last_order.id])
                if has_next
                else None
            )
            prev_cursor = (
                encode_cursor([first_order.created_at.isoformat(), first_order.id])
                if has_prev
                else None
            )
        else:
            has_next = False
            has_prev = False
            next_cursor = None
            prev_cursor = None

    elif cursor:
        try:
            c_created_at_iso, c_id = decode_cursor(cursor)
            c_created_at = datetime.datetime.fromisoformat(c_created_at_iso)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid cursor"
            )
        cursor_filter = Q(created_at__lt=c_created_at) | Q(
            created_at=c_created_at, id__lt=c_id
        )
        query_filter = base_filter & cursor_filter
        orders_db = (
            await Order.filter(query_filter)
            .prefetch_related("user", "items__item", "events")
            .order_by("-created_at", "-id")
            .limit(limit + 1)
        )
        has_next = len(orders_db) > limit
        orders_db = orders_db[:limit]

        if orders_db:
            first_order = orders_db[0]
            last_order = orders_db[-1]
            before_filter = base_filter & (
                Q(created_at__gt=first_order.created_at)
                | Q(created_at=first_order.created_at, id__gt=first_order.id)
            )
            has_prev = await Order.filter(before_filter).exists()
            next_cursor = (
                encode_cursor([last_order.created_at.isoformat(), last_order.id])
                if has_next
                else None
            )
            prev_cursor = (
                encode_cursor([first_order.created_at.isoformat(), first_order.id])
                if has_prev
                else None
            )
        else:
            has_next = False
            has_prev = False
            next_cursor = None
            prev_cursor = None

    else:
        orders_db = (
            await Order.filter(base_filter)
            .prefetch_related("user", "items__item", "events")
            .order_by("-created_at", "-id")
            .limit(limit + 1)
        )
        has_next = len(orders_db) > limit
        orders_db = orders_db[:limit]
        has_prev = False

        if orders_db:
            first_order = orders_db[0]
            last_order = orders_db[-1]
            next_cursor = (
                encode_cursor([last_order.created_at.isoformat(), last_order.id])
                if has_next
                else None
            )
            prev_cursor = None
        else:
            next_cursor = None
            prev_cursor = None

    items = [await _to_order_public_schema(order) for order in orders_db]
    return PaginatedOrderResponse(
        items=items,
        next_cursor=next_cursor,
        prev_cursor=prev_cursor,
        has_next=has_next,
        has_prev=has_prev,
    )


async def create_new_order(
    order_data: OrderCreateSchema, current_user: AuthUser
) -> Order:
    async with in_transaction() as conn:
        new_order_id_str = await Order.generate_next_order_id()
        order = await Order.create(
            public_id=generate_ksuid(),
            order_id=new_order_id_str,
            contact_name=order_data.contact_name,
            contact_email=order_data.contact_email,
            delivery_address=order_data.delivery_address,
            status="placed",
            user=current_user,
            using_db=conn,
        )
        await _process_order_items(order, order_data.items, conn)
        await OrderEvent.create(
            public_id=generate_ksuid(),
            order=order,
            event_type="order_placed",
            data={"message": "Order created successfully."},
            using_db=conn,
        )
        # No explicit commit needed, transaction context manager handles it.

    # Fetch the full order with relations for response after transaction commits
    # This is important to ensure all related data (user, items, events) is loaded
    # before it's passed to _to_order_public_schema or used otherwise.
    full_order = await Order.get(id=order.id).prefetch_related(
        "user", "items__item", "events"
    )
    return full_order


async def ship_existing_order(
    order_public_id: str, ship_data: Optional[OrderShipRequestSchema]
) -> Order:
    order = await Order.get_or_none(public_id=order_public_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found."
        )
    if order.status in ["shipped", "cancelled"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Order is already {order.status}.",
        )

    async with in_transaction() as conn:
        # Lock the order row for update
        order_locked = await Order.get(id=order.id, using_db=conn).select_for_update()

        order_locked.status = "shipped"
        await order_locked.save(using_db=conn, update_fields=["status"])

        event_data = ship_data.model_dump(exclude_none=True) if ship_data else {}
        if not event_data:  # Ensure there's always a message
            event_data = {"message": "Order marked as shipped."}

        await OrderEvent.create(
            public_id=generate_ksuid(),
            order=order_locked,
            event_type="order_shipped",
            data=event_data,
            using_db=conn,
        )
        # Transaction is committed automatically upon exiting the 'async with' block

    # Fetch the full order with all relations to return a complete view
    full_order_after_ship = await Order.get(id=order.id).prefetch_related(
        "user", "items__item", "events"
    )
    return full_order_after_ship


async def cancel_existing_order(
    order_public_id: str, cancel_data: Optional[OrderCancelRequestSchema]
) -> Order:
    order = await Order.get_or_none(public_id=order_public_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found."
        )
    if order.status == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Order already cancelled."
        )
    if order.status == "shipped" and not (cancel_data and cancel_data.reason):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Shipped order cancellation requires a reason.",
        )

    # Determine if stock should be replenished based on current order status
    should_replenish = order.status not in ["delivered", "shipped"]

    async with in_transaction() as conn:
        order_locked = await Order.get(id=order.id, using_db=conn).select_for_update()

        order_locked.status = "cancelled"
        await order_locked.save(using_db=conn, update_fields=["status"])

        if should_replenish:
            order_items_for_replenish = (
                await OrderItem.filter(order_id=order_locked.id)
                .select_related("item")
                .using_db(conn)
            )
            for oi in order_items_for_replenish:
                inv_item = await InventoryItem.get(
                    id=oi.item_id, using_db=conn
                ).select_for_update()
                inv_item.quantity += oi.quantity
                await inv_item.save(using_db=conn, update_fields=["quantity"])

        event_data = cancel_data.model_dump(exclude_none=True) if cancel_data else {}
        event_data["stock_replenished"] = should_replenish
        if not (
            cancel_data and cancel_data.reason
        ):
            event_data.setdefault("message", "Order cancelled.")

        await OrderEvent.create(
            public_id=generate_ksuid(),
            order=order_locked,
            event_type="order_cancelled",
            data=event_data,
            using_db=conn,
        )
        # Transaction commits automatically

    full_order_after_cancel = await Order.get(id=order.id).prefetch_related(
        "user", "items__item", "events"
    )
    return full_order_after_cancel


async def _process_order_items(order, items, conn):
    for item_data in items:
        inventory_item = await InventoryItem.get_or_none(
            public_id=item_data.product_public_id, using_db=conn
        ).select_for_update()
        if not inventory_item:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Item {item_data.product_public_id} not found.",
            )
        if inventory_item.quantity < item_data.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Not enough stock for {inventory_item.name}.",
            )

        inventory_item.quantity -= item_data.quantity
        await inventory_item.save(using_db=conn, update_fields=["quantity"])
        await OrderItem.create(
            public_id=generate_ksuid(),
            order=order,
            item_id=inventory_item.id,
            quantity=item_data.quantity,
            price_amount=item_data.price_at_purchase.amount,
            price_currency=item_data.price_at_purchase.currency,
            using_db=conn,
        )

async def _to_order_public_schema(order: Order) -> OrderPublicSchema:
    user_resp = (
        UserResponse.model_validate(order.user)
        if order.user and hasattr(order, "user")
        else None
    )

    items_resp = [
        OrderItemPublicSchema(
            public_id=item.public_id,
            product_public_id=item.item.public_id,
            quantity=item.quantity,
            price_at_purchase=MoneySchema(
                amount=item.price_at_purchase.amount,
                currency=item.price_at_purchase.currency.code,
            ),
        )
        for item in order.items
    ]

    events_resp = []
    if hasattr(order, "events"):
        events_resp = [
            OrderEventPublicSchema.model_validate(e) for e in await order.events.all()
        ]

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
