import logging
import logging
from fastapi import APIRouter, HTTPException, Depends, status, Query # Added status and Query
from tortoise.transactions import in_transaction
from tortoise.exceptions import DoesNotExist
from typing import List, Optional, Annotated # Added Annotated

from ..models import Order, OrderItem, OrderEvent, InventoryItem, User, generate_ksuid # Added User
from .. import auth # Added auth
from ..schemas import (
    OrderCreateSchema,
    OrderPublicSchema,
    OrderItemCreateSchema,
    OrderItemPublicSchema,
    OrderEventPublicSchema,
    OrderShipRequestSchema,
    OrderCancelRequestSchema,
    UserResponse # Added UserResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/orders",
    tags=["Orders"],
)

async def to_full_order(order: Order) -> OrderPublicSchema:
    # Ensure order.user is available (prefetched) before calling this helper
    user_data_for_schema = None
    if hasattr(order, 'user') and order.user: # Check if 'user' attribute exists and is not None
        # Accessing order.user here assumes it's already fetched (e.g. via .prefetch_related("user"))
        # If order.user is a Pydantic model already (e.g. if User model itself was returned by query), fine.
        # If order.user is a Tortoise model instance, model_validate will convert it.
        user_data_for_schema = UserResponse.model_validate(order.user)

    return OrderPublicSchema(
        contact_name=order.contact_name,
        contact_email=order.contact_email,
        delivery_address=order.delivery_address,
        public_id=order.public_id,
        order_id=order.order_id,
        status=order.status,
        user=user_data_for_schema, # Assign the Pydantic UserResponse model
        items=[OrderItemPublicSchema(product_public_id=f"{(await i.item.first()).public_id}", quantity=i.quantity, public_id=i.public_id, price_at_purchase=i.price_at_purchase) for i in await order.items.all()], # Use .all() for related manager
        events=[OrderEventPublicSchema(public_id=e.public_id, event_type=e.event_type, data=e.data, occurred_at=e.occurred_at) for e in await order.events.all()], # Use .all() for related manager
        created_at=order.created_at,
        updated_at=order.updated_at,
    )

@router.post("/", response_model=OrderPublicSchema, status_code=status.HTTP_201_CREATED) # Added status
async def create_order(
    order_data: OrderCreateSchema,
    current_user: Annotated[User, Depends(auth.get_current_active_user)]
):
    # Schema already validates items is not empty via min_length=1 in OrderCreateSchema

    async with in_transaction() as conn:
        new_order_id_str = await Order.generate_next_order_id()

        # Ensure all fields from OrderBase are passed, matching Order model
        order = await Order.create(
            public_id=generate_ksuid(),
            order_id=new_order_id_str,
            contact_name=order_data.contact_name,
            contact_email=order_data.contact_email,
            delivery_address=order_data.delivery_address,
            status="placed", # Initial status
            user=current_user, # Associate order with the current user
            using_db=conn
        )

        order_items_to_create = []
        items_to_update_stock = [] # To store (inventory_item, quantity_to_decrement)

        for item_data in order_data.items:
            # Lock the inventory item row for update to prevent race conditions
            inventory_item = await InventoryItem.get_or_none(
                public_id=item_data.product_public_id,
                using_db=conn
            ).select_for_update() # Lock the row

            if not inventory_item:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, # Corrected status code
                    detail=f"Inventory item with public_id {item_data.product_public_id} not found."
                )

            if inventory_item.quantity < item_data.quantity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Not enough stock for {inventory_item.name}. Available: {inventory_item.quantity}, Requested: {item_data.quantity}"
                )

            # Store for batch update later (or update immediately if preferred, but batch can be slightly more performant)
            # For atomicity, immediate update within loop is also fine as it's part of the transaction.
            # Let's do immediate update for clarity here.
            inventory_item.quantity -= item_data.quantity
            await inventory_item.save(using_db=conn, update_fields=['quantity'])

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

        # Fetch the complete order object with related items, events, and user for the response
        full_order = await Order.get_or_none(id=order.id, using_db=conn).prefetch_related("items", "events", "user")
        if not full_order:
            # This case should ideally not be reached if creation was successful
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve created order details.")

        return await to_full_order(full_order)


@router.get("/", response_model=List[OrderPublicSchema])
async def list_orders(
    current_user: Annotated[User, Depends(auth.get_current_active_user)],
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Items per page")
):
    """
    List orders.
    - Admins can see all orders.
    - Customers can only see their own orders.
    Orders are returned sorted by creation date, newest first.
    """
    offset = (page - 1) * size
    query = Order.all().prefetch_related("items", "events", "user").order_by("-created_at")

    if current_user.role != "admin":
        query = query.filter(user_id=current_user.id)

    orders = await query.offset(offset).limit(size)

    # TODO: Add pagination metadata to response if creating a PaginatedOrderResponse schema
    # total_query = Order.all()
    # if current_user.role != "admin":
    #     total_query = total_query.filter(user_id=current_user.id)
    # total_count = await total_query.count()

    return [await to_full_order(order) for order in orders]


@router.get("/{order_public_id}", response_model=OrderPublicSchema)
async def get_order(
    order_public_id: str,
    current_user: Annotated[User, Depends(auth.get_current_active_user)]
):
    try:
        order = await Order.get(public_id=order_public_id).prefetch_related(
            "items", "events", "user"
        )
    except DoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Order with public_id {order_public_id} not found.")

    # Authorization: Admin can see any order, customers can only see their own.
    if current_user.role != "admin" and order.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this order.")

    return await to_full_order(order)


@router.patch("/{order_public_id}/ship", response_model=OrderPublicSchema)
async def ship_order(
    order_public_id: str,
    current_admin: Annotated[User, Depends(auth.get_current_active_admin_user)],
    ship_data: Optional[OrderShipRequestSchema] = None
):
    try:
        order = await Order.get(public_id=order_public_id).prefetch_related("items", "events", "user")
    except DoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Order with public_id {order_public_id} not found.")

    if order.status == "shipped":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order is already shipped.")
    if order.status == "cancelled":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot ship a cancelled order.")

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
        # Refresh events for the response (user is already fetched via prefetch_related)
        await order.fetch_related("events", using_db=conn)

    return await to_full_order(order)


@router.patch("/{order_public_id}/cancel", response_model=OrderPublicSchema)
async def cancel_order(
    order_public_id: str,
    current_admin: Annotated[User, Depends(auth.get_current_active_admin_user)],
    cancel_data: Optional[OrderCancelRequestSchema] = None
):
    try:
        order = await Order.get(public_id=order_public_id).prefetch_related("items", "events", "user")
    except DoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Order with public_id {order_public_id} not found.")

    if order.status == "cancelled":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order is already cancelled.")

    # Admins can cancel shipped orders if a reason is given.
    if order.status == "shipped" and not (cancel_data and cancel_data.reason): # Allow admin to cancel shipped order if reason provided
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Shipped order cancellation requires a reason for admin.")

    # Business rule: Only replenish stock if order was not 'delivered' (assuming 'delivered' is a terminal state for stock)
    # For simplicity, we'll replenish unless it was 'delivered'.
    # A more robust system might have specific conditions or item return process.
    should_replenish_stock = order.status != "delivered" # Example condition

    async with in_transaction() as conn:
        order.status = "cancelled"
        await order.save(using_db=conn, update_fields=['status'])

        # Replenish stock if applicable
        if should_replenish_stock:
            order_items = await order.items.all().select_related("item").using_db(conn) # Fetch items and their related inventory item
            for order_item in order_items:
                inventory_item = order_item.item # This is the InventoryItem instance
                if inventory_item: # Should always exist if DB integrity is maintained
                    # Lock inventory item row before updating
                    await inventory_item.fetch_related('category') # To ensure it's fully loaded before save, or select_for_update
                    # It's better to re-fetch with select_for_update if high concurrency is a concern for cancellations
                    # For now, we assume order_item.item is sufficiently up-to-date for quantity.
                    # A stricter way:
                    # inventory_item_locked = await InventoryItem.get(id=inventory_item.id, using_db=conn).select_for_update()
                    # inventory_item_locked.quantity += order_item.quantity
                    # await inventory_item_locked.save(using_db=conn, update_fields=['quantity'])
                    # Simpler way for now:
                    inventory_item.quantity += order_item.quantity
                    await inventory_item.save(using_db=conn, update_fields=['quantity'])
                    logger.info(f"Replenished {order_item.quantity} for item {inventory_item.name} (ID: {inventory_item.id}) from cancelled order {order.order_id}")


        event_data = {}
        if cancel_data and cancel_data.reason:
            event_data["reason"] = cancel_data.reason
        event_data["stock_replenished"] = should_replenish_stock


        await OrderEvent.create(
            public_id=generate_ksuid(),
            order=order,
            event_type="order_cancelled",
            data=event_data,
            using_db=conn
        )
        # Refresh events for the response (user is already fetched via prefetch_related)
        await order.fetch_related("events", using_db=conn)

    return await to_full_order(order)
