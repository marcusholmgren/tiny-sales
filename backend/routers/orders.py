from fastapi import APIRouter, HTTPException, Depends
from tortoise.transactions import in_transaction
from tortoise.exceptions import DoesNotExist # Add this import
from typing import List

from backend.models import Order, OrderItem, OrderEvent, InventoryItem
from backend.schemas import OrderCreateSchema, OrderPublicSchema, OrderItemCreateSchema
from backend.models import generate_ksuid # Assuming generate_ksuid is in backend.models

router = APIRouter(
    prefix="/orders",
    tags=["Orders"],
)

@router.post("/", response_model=OrderPublicSchema, status_code=201)
async def create_order(order_data: OrderCreateSchema):
    # Schema already validates items is not empty via min_length=1 in OrderCreateSchema

    async with in_transaction() as conn:
        new_order_id_str = await Order.generate_next_order_id()

        order_public_id = generate_ksuid()
        # Ensure all fields from OrderBase are passed, matching Order model
        order = await Order.create(
            public_id=order_public_id,
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
                    public_id=generate_ksuid(), # KSUID for OrderItem
                    order=order,
                    item_id=inventory_item.id, # FK to InventoryItem's primary key
                    quantity=item_data.quantity,
                    price_at_purchase=item_data.price_at_purchase # From updated OrderItemCreateSchema
                )
            )

        if not order_items_to_create:
             # This check is technically redundant if OrderCreateSchema.items has min_length=1
             raise HTTPException(status_code=400, detail="Order must contain at least one item.")

        await OrderItem.bulk_create(order_items_to_create, using_db=conn)

        # Create initial order event
        await OrderEvent.create(
            public_id=generate_ksuid(), # KSUID for OrderEvent
            order=order,
            event_type="order_placed",
            data={"message": "Order created successfully."}, # Example data
            using_db=conn
        )

        # Fetch the complete order object with related items and events for the response
        # This ensures the response matches OrderPublicSchema
        full_order = await Order.get_or_none(id=order.id, using_db=conn).prefetch_related("items", "events")
        if not full_order:
            # This case should ideally not be reached if creation was successful
            raise HTTPException(status_code=500, detail="Failed to retrieve created order details.")

        return full_order


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
        return order
    except DoesNotExist:
        raise HTTPException(status_code=404, detail=f"Order with public_id {order_public_id} not found.")
