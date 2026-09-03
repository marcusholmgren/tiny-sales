"""Service functions for order management feature."""

# External dependencies
import datetime
from tortoise.transactions import in_transaction
from tortoise.exceptions import DoesNotExist
from tortoise.expressions import Q
from fastapi import HTTPException, status  # For exceptions, status codes

# Typing
from typing import List, Optional

# Models from this feature and related features
from .models import Order  # Local models
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

# State Machine imports
from ...common.state_machine import InvalidTransition
from .state_machine import OrderState, OrderEventTrigger, OrderCtx, order_sm

# Utilities
from ...common.models import generate_ksuid  # KSUID generation
from ...common import MoneySchema
from ...common.cursor import encode_cursor, decode_cursor


async def get_order_by_public_id(order_public_id: str, current_user: AuthUser) -> Order:
    """Retrieve an order by its public ID and verify permissions."""
    try:
        order = await Order.get(public_id=order_public_id).prefetch_related(
            "user", "items__item", "events"
        )
    except DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order {order_public_id} not found.",
        )

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
    """Retrieve a paginated list of orders for the user/admin."""
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
    """Create a new order using the state machine."""
    async with in_transaction() as conn:
        new_order_id_str = await Order.generate_next_order_id()
        order = await Order.create(
            public_id=generate_ksuid(),
            order_id=new_order_id_str,
            contact_name=order_data.contact_name,
            contact_email=order_data.contact_email,
            delivery_address=order_data.delivery_address,
            status=OrderState.PENDING_PAYMENT.value,
            user=current_user,
            using_db=conn,
        )

        curr_state = OrderState(order.status)
        ctx = OrderCtx(
            order=order,
            conn=conn,
            from_state=curr_state,
            create_data=order_data,
        )

        try:
            next_state = await order_sm.ahandle(
                ctx, curr_state, OrderEventTrigger.PLACE
            )
        except InvalidTransition as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
            )

        order.status = next_state.value
        await order.save(using_db=conn, update_fields=["status"])

    full_order = await Order.get(id=order.id).prefetch_related(
        "user", "items__item", "events"
    )
    return full_order


async def ship_existing_order(
    order_public_id: str, ship_data: Optional[OrderShipRequestSchema]
) -> Order:
    """Mark an existing order as shipped using the state machine."""
    order = await Order.get_or_none(public_id=order_public_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found."
        )

    async with in_transaction() as conn:
        order_locked = await Order.get(id=order.id, using_db=conn).select_for_update()

        curr_state = OrderState(order_locked.status)
        ctx = OrderCtx(
            order=order_locked,
            conn=conn,
            from_state=curr_state,
            ship_data=ship_data,
        )

        try:
            next_state = await order_sm.ahandle(ctx, curr_state, OrderEventTrigger.SHIP)
        except InvalidTransition:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Order is already {order_locked.status}.",
            )

        order_locked.status = next_state.value
        await order_locked.save(using_db=conn, update_fields=["status"])

    full_order_after_ship = await Order.get(id=order.id).prefetch_related(
        "user", "items__item", "events"
    )
    return full_order_after_ship


async def cancel_existing_order(
    order_public_id: str, cancel_data: Optional[OrderCancelRequestSchema]
) -> Order:
    """Cancel an existing order using the state machine."""
    order = await Order.get_or_none(public_id=order_public_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found."
        )

    async with in_transaction() as conn:
        order_locked = await Order.get(id=order.id, using_db=conn).select_for_update()

        curr_state = OrderState(order_locked.status)
        ctx = OrderCtx(
            order=order_locked,
            conn=conn,
            from_state=curr_state,
            cancel_data=cancel_data,
        )

        try:
            next_state = await order_sm.ahandle(
                ctx, curr_state, OrderEventTrigger.CANCEL
            )
        except InvalidTransition:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Order already cancelled."
                if curr_state == OrderState.CANCELLED
                else f"Cannot cancel order in state {curr_state.value}.",
            )

        order_locked.status = next_state.value
        await order_locked.save(using_db=conn, update_fields=["status"])

    full_order_after_cancel = await Order.get(id=order.id).prefetch_related(
        "user", "items__item", "events"
    )
    return full_order_after_cancel


async def _to_order_public_schema(order: Order) -> OrderPublicSchema:
    """Convert an Order ORM model into OrderPublicSchema."""
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
