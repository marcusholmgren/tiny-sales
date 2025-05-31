import logging
from fastapi import APIRouter, HTTPException, Depends
from tortoise.transactions import in_transaction
from tortoise.exceptions import DoesNotExist
from typing import List, Optional

from backend.models import Order, OrderItem, OrderEvent, InventoryItem, generate_ksuid
from backend.schemas import (
    OrderCreateSchema,
    OrderPublicSchema,
    OrderItemCreateSchema,
    OrderItemPublicSchema,
    OrderEventPublicSchema,
    OrderShipRequestSchema, # To be created
    OrderCancelRequestSchema # To be created
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/orders",
    tags=["Orders"],
)

async def to_full_order(order: Order) -> OrderPublicSchema:
    return OrderPublicSchema(
        contact_name=order.contact_name,
        contact_email=order.contact_email,
        delivery_address=order.delivery_address,
        public_id=order.public_id,
        order_id=order.order_id,
        status=order.status,
        items=[OrderItemPublicSchema(product_public_id=f"{(await i.item.first()).public_id}", quantity=i.quantity, public_id=i.public_id, price_at_purchase=i.price_at_purchase) for i in order.items],
        events=[OrderEventPublicSchema(public_id=e.public_id, event_type=e.event_type, data=e.data, occurred_at=e.occurred_at) for e in order.events],
        created_at=order.created_at,
        updated_at=order.updated_at,
    )

@router.post("/", response_model=OrderPublicSchema, status_code=201)
async def create_order(order_data: OrderCreateSchema):
    # Schema already validates items is not empty via min_length=1 in OrderCreateSchema

    async with in_transaction() as conn:
        new_order_id_str = await Order.generate_next_order_id()

        # Ensure all fields from OrderBase are passed, matching Order model
        order = await Order.create(
            public_id=generate_ksuid(),
            order_id=new_order_id_str, # This is internal_order_id
            contact_name=order_data.contact_name,
            contact_email=order_data.contact_email,
            delivery_address=order_data.delivery_address, # Matches simplified model field
            status="placed", # Initial status
            using_db=conn
        )

        order_items_to_create = []
        for item_data in order_data.items:
            inventory_item = await InventoryItem.get_or_none(public_id=item_data.product_public_id, using_db=conn)
            if not inventory_item:
                raise HTTPException(
                    status_code=400,
                    detail=f"Inventory item with public_id {item_data.product_public_id} not found."
                )

            # Optional: Inventory quantity check (adjust based on business rules)
            # if inventory_item.quantity < item_data.quantity:
            #     raise HTTPException(status_code=400, detail=f"Not enough stock for {inventory_item.name}")
            # inventory_item.quantity -= item_data.quantity
            # await inventory_item.save(using_db=conn, update_fields=['quantity'])

            order_items_to_create.append(
                OrderItem(
                    public_id=generate_ksuid(),
                    order=order,
                    item_id=inventory_item.id, # FK to InventoryItem's primary key
                    quantity=item_data.quantity,
                    price_at_purchase=item_data.price_at_purchase # From updated OrderItemCreateSchema
                )
            )
        logger.info(f"Order: {order_items_to_create[0]}")
        if not order_items_to_create:
             # This check is technically redundant if OrderCreateSchema.items has min_length=1
             raise HTTPException(status_code=400, detail="Order must contain at least one item.")

        await OrderItem.bulk_create(order_items_to_create, using_db=conn)

        # Create initial order event
        await OrderEvent.create(
            public_id=generate_ksuid(),
            order=order,
            event_type="order_placed",
            data={"message": "Order created successfully."}, # Example data
            using_db=conn
        )

        await conn.commit()

        # Fetch the complete order object with related items and events for the response
        # This ensures the response matches OrderPublicSchema
        full_order = await Order.get_or_none(id=order.id, using_db=conn).prefetch_related("items", "events")
        if not full_order:
            # This case should ideally not be reached if creation was successful
            raise HTTPException(status_code=500, detail="Failed to retrieve created order details.")

        return await to_full_order(full_order)


@router.get("/{order_public_id}", response_model=OrderPublicSchema)
async def get_order(order_public_id: str):
    try:
        order = await Order.get(public_id=order_public_id).prefetch_related(
            "items",
            "events" # Tortoise by default orders by PK, 'events' are ordered by 'occurred_at' in model Meta
        )
        # If OrderEvent.Meta.ordering is not respected by prefetch or needs to be explicit:
        # order = await Order.get(public_id=order_public_id).prefetch_related("items")
        # events = await OrderEvent.filter(order_id=order.id).order_by("occurred_at")
        # # Manually assign events to a pydantic model if not directly mapped
        # # However, OrderPublicSchema expects 'events' to be populated from the model.
        # # The prefetch_related should work given the OrderEvent.Meta.ordering.

        # The OrderPublicSchema expects related fields to be populated.
        # Tortoise ORM's .prefetch_related() and Pydantic's from_orm (from_attributes=True)
        # should handle the conversion correctly.
        return await to_full_order(order)
    except DoesNotExist:
        raise HTTPException(status_code=404, detail=f"Order with public_id {order_public_id} not found.")


@router.patch("/{order_public_id}/ship", response_model=OrderPublicSchema)
async def ship_order(order_public_id: str, ship_data: Optional[OrderShipRequestSchema] = None):
    try:
        order = await Order.get(public_id=order_public_id).prefetch_related("items", "events")
    except DoesNotExist:
        raise HTTPException(status_code=404, detail=f"Order with public_id {order_public_id} not found.")

    if order.status == "shipped":
        raise HTTPException(status_code=400, detail="Order is already shipped.")
    if order.status == "cancelled":
        raise HTTPException(status_code=400, detail="Cannot ship a cancelled order.")

    async with in_transaction() as conn:
        order.status = "shipped"
        await order.save(using_db=conn, update_fields=['status'])

        event_data = {}
        if ship_data:
            if ship_data.tracking_number:
                event_data["tracking_number"] = ship_data.tracking_number
            if ship_data.shipping_provider:
                event_data["shipping_provider"] = ship_data.shipping_provider

        await OrderEvent.create(
            public_id=generate_ksuid(),
            order=order,
            event_type="order_shipped",
            data=event_data if event_data else {"message": "Order marked as shipped."},
            using_db=conn
        )
        # Refresh events for the response
        await order.fetch_related("events", using_db=conn)


    return await to_full_order(order)


@router.patch("/{order_public_id}/cancel", response_model=OrderPublicSchema)
async def cancel_order(order_public_id: str, cancel_data: Optional[OrderCancelRequestSchema] = None):
    try:
        order = await Order.get(public_id=order_public_id).prefetch_related("items", "events")
    except DoesNotExist:
        raise HTTPException(status_code=404, detail=f"Order with public_id {order_public_id} not found.")

    if order.status == "cancelled":
        raise HTTPException(status_code=400, detail="Order is already cancelled.")
    if order.status == "shipped" and not (cancel_data and cancel_data.reason and "customer requested" in cancel_data.reason.lower()): # Example condition, adjust as needed
        # More complex cancellation rules might be needed depending on whether a shipped order can be cancelled.
        # For now, let's assume a shipped order cannot be easily cancelled unless for specific reasons.
        # Allow cancellation even if shipped, if a reason is provided. Business logic might differ.
        raise HTTPException(status_code=400, detail="Cannot cancel a shipped order without a valid reason.")


    async with in_transaction() as conn:
        order.status = "cancelled"
        await order.save(using_db=conn, update_fields=['status'])

        event_data = {}
        if cancel_data and cancel_data.reason:
            event_data["reason"] = cancel_data.reason

        await OrderEvent.create(
            public_id=generate_ksuid(),
            order=order,
            event_type="order_cancelled",
            data=event_data if event_data else {"message": "Order marked as cancelled."},
            using_db=conn
        )
        # Refresh events for the response
        await order.fetch_related("events", using_db=conn)

    return await to_full_order(order)
