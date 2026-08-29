"""Order state machine definitions and transition handlers."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional
from fastapi import HTTPException, status

from ...common.state_machine import StateMachine, InvalidTransition
from ...common.models import generate_ksuid
from .models import Order, OrderItem, OrderEvent
from ..inventory.models import InventoryItem
from .schemas import OrderCreateSchema, OrderShipRequestSchema, OrderCancelRequestSchema


class OrderState(str, Enum):
    """Enumeration of order statuses."""

    PENDING_PAYMENT = "pending_payment"
    PLACED = "placed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class OrderEventTrigger(str, Enum):
    """Enumeration of events that trigger order state transitions."""

    PLACE = "place"
    SHIP = "ship"
    CANCEL = "cancel"


@dataclass
class OrderCtx:
    """Context object holding data needed during order state transitions."""

    order: Order
    conn: Any
    from_state: OrderState
    create_data: Optional[OrderCreateSchema] = None
    ship_data: Optional[OrderShipRequestSchema] = None
    cancel_data: Optional[OrderCancelRequestSchema] = None


# Order State Machine Singleton
order_sm: StateMachine[OrderState, OrderEventTrigger, OrderCtx] = StateMachine()


@order_sm.transition(
    from_state=OrderState.PENDING_PAYMENT,
    event=OrderEventTrigger.PLACE,
    to_state=OrderState.PLACED,
)
async def on_place(ctx: OrderCtx) -> None:
    """Action executed when an order is placed."""
    if not ctx.create_data:
        return

    for item_data in ctx.create_data.items:
        inventory_item = await InventoryItem.get_or_none(
            public_id=item_data.product_public_id, using_db=ctx.conn
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
        await inventory_item.save(using_db=ctx.conn, update_fields=["quantity"])
        await OrderItem.create(
            public_id=generate_ksuid(),
            order=ctx.order,
            item_id=inventory_item.id,
            quantity=item_data.quantity,
            price_amount=item_data.price_at_purchase.amount,
            price_currency=item_data.price_at_purchase.currency,
            using_db=ctx.conn,
        )

    await OrderEvent.create(
        public_id=generate_ksuid(),
        order=ctx.order,
        event_type="order_placed",
        data={"message": "Order created successfully."},
        using_db=ctx.conn,
    )


@order_sm.transition(
    from_state=[OrderState.PENDING_PAYMENT, OrderState.PLACED],
    event=OrderEventTrigger.SHIP,
    to_state=OrderState.SHIPPED,
)
async def on_ship(ctx: OrderCtx) -> None:
    """Action executed when an order is shipped."""
    event_data = (
        ctx.ship_data.model_dump(exclude_none=True) if ctx.ship_data else {}
    )
    if not event_data:
        event_data = {"message": "Order marked as shipped."}

    await OrderEvent.create(
        public_id=generate_ksuid(),
        order=ctx.order,
        event_type="order_shipped",
        data=event_data,
        using_db=ctx.conn,
    )


@order_sm.transition(
    from_state=[
        OrderState.PENDING_PAYMENT,
        OrderState.PLACED,
        OrderState.SHIPPED,
    ],
    event=OrderEventTrigger.CANCEL,
    to_state=OrderState.CANCELLED,
)
async def on_cancel(ctx: OrderCtx) -> None:
    """Action executed when an order is cancelled."""
    if ctx.from_state == OrderState.SHIPPED and not (
        ctx.cancel_data and ctx.cancel_data.reason
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Shipped order cancellation requires a reason.",
        )

    should_replenish = ctx.from_state not in [
        OrderState.DELIVERED,
        OrderState.SHIPPED,
        OrderState.COMPLETED,
    ]

    if should_replenish:
        order_items_for_replenish = (
            await OrderItem.filter(order_id=ctx.order.id)
            .select_related("item")
            .using_db(ctx.conn)
        )
        for oi in order_items_for_replenish:
            inv_item = await InventoryItem.get(
                id=oi.item_id, using_db=ctx.conn
            ).select_for_update()
            inv_item.quantity += oi.quantity
            await inv_item.save(using_db=ctx.conn, update_fields=["quantity"])

    event_data = (
        ctx.cancel_data.model_dump(exclude_none=True) if ctx.cancel_data else {}
    )
    event_data["stock_replenished"] = should_replenish
    if not (ctx.cancel_data and ctx.cancel_data.reason):
        event_data.setdefault("message", "Order cancelled.")

    await OrderEvent.create(
        public_id=generate_ksuid(),
        order=ctx.order,
        event_type="order_cancelled",
        data=event_data,
        using_db=ctx.conn,
    )
