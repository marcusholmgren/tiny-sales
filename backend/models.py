import datetime
from tortoise import fields, models
from tortoise.contrib.pydantic import pydantic_model_creator
from ksuid import KsuidMs

def generate_ksuid():
    return KsuidMs()

class TimestampMixin(models.Model):
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        abstract = True

class InventoryItem(TimestampMixin):
    id = fields.IntField(pk=True)
    public_id = fields.CharField(max_length=27, unique=True, default=generate_ksuid, index=True)
    name = fields.CharField(max_length=255)
    quantity = fields.IntField(default=0)
    deleted_at = fields.DatetimeField(null=True, default=None) # For soft delete

    orders: fields.ReverseRelation["OrderItem"] # M2M through OrderItem

    def __str__(self):
        return f"{self.name} (Stock: {self.quantity})"

    class Meta:
        table = "inventory_items"

class Order(TimestampMixin):
    id = fields.IntField(pk=True) # Internal auto-incrementing ID
    order_id = fields.CharField(max_length=50, unique=True, description="Pattern: <year+0000> e.g. 20250001") # User-facing order ID
    public_id = fields.CharField(max_length=27, unique=True, default=generate_ksuid, index=True)

    # Contact and Delivery Information
    contact_name = fields.CharField(max_length=255)
    contact_email = fields.CharField(max_length=255) # Consider adding validation
    delivery_address = fields.TextField()

    status = fields.CharField(max_length=50, default="pending_payment") # Current status of the order

    items: fields.ReverseRelation["OrderItem"]
    events: fields.ReverseRelation["OrderEvent"]

    @classmethod
    async def generate_next_order_id(cls):
        year_str = str(datetime.datetime.now().year)
        last_order = await cls.filter(order_id__startswith=year_str).order_by('-order_id').first()
        if last_order and last_order.order_id.startswith(year_str):
            last_sequence = int(last_order.order_id[len(year_str):])
            next_sequence = last_sequence + 1
        else:
            next_sequence = 1
        return f"{year_str}{next_sequence:04d}"

    def __str__(self):
        return f"Order {self.order_id} ({self.public_id}) - Status: {self.status}"

    class Meta:
        table = "orders"


class OrderItem(TimestampMixin):
    id = fields.IntField(pk=True)
    order: fields.ForeignKeyRelation[Order] = fields.ForeignKeyField(
        "models.Order", related_name="items", on_delete=fields.CASCADE
    )
    item: fields.ForeignKeyRelation[InventoryItem] = fields.ForeignKeyField(
        "models.InventoryItem", related_name="order_items", on_delete=fields.RESTRICT # Prevent deleting inventory item if part of an order
    )
    quantity = fields.IntField()
    price_at_purchase = fields.FloatField() # Price of the item at the time of purchase

    def __str__(self):
        return f"{self.quantity} x {self.item.name} for Order {self.order.order_id}"

    class Meta:
        table = "order_items"
        unique_together = (("order", "item"),) # Ensure an item is not added twice to the same order; update quantity instead


class OrderEvent(models.Model): # No TimestampMixin, occurred_at is specific
    id = fields.IntField(pk=True)
    order: fields.ForeignKeyRelation[Order] = fields.ForeignKeyField(
        "models.Order", related_name="events", on_delete=fields.CASCADE
    )
    event_type = fields.CharField(max_length=100) # e.g., "order_placed", "payment_confirmed", "order_packed", "order_shipped", "order_delivered", "order_cancelled"
    data = fields.JSONField(null=True) # Store relevant data, e.g., tracking number for "shipped", reason for "cancelled"
    occurred_at = fields.DatetimeField(auto_now_add=True)

    def __str__(self):
        return f"Event '{self.event_type}' for Order {self.order.order_id} at {self.occurred_at}"

    class Meta:
        table = "order_events"
        ordering = ["occurred_at"]


# Pydantic models for API validation and response
# These will be generated after Tortoise is initialized usually,
# but we can define them here for clarity or use them in main.py

InventoryItem_Pydantic = pydantic_model_creator(InventoryItem, name="InventoryItem")
InventoryItemIn_Pydantic = pydantic_model_creator(InventoryItem, name="InventoryItemIn", exclude_readonly=True, exclude=("public_id", "deleted_at"))

Order_Pydantic = pydantic_model_creator(Order, name="Order")
# For creating an order, we'll likely have a more complex input model
# OrderIn_Pydantic = pydantic_model_creator(Order, name="OrderIn", exclude_readonly=True, exclude=("public_id", "order_id", "status"))

OrderItem_Pydantic = pydantic_model_creator(OrderItem, name="OrderItem")
# OrderItemIn_Pydantic = pydantic_model_creator(OrderItem, name="OrderItemIn", exclude_readonly=True)


OrderEvent_Pydantic = pydantic_model_creator(OrderEvent, name="OrderEvent")

# More specific Pydantic models for request bodies and responses will be defined in the FastAPI app (main.py or routers)
# For example, a request to create an order would look different.
