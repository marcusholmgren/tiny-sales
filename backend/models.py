import datetime
from tortoise import fields, models
# from tortoise.contrib.pydantic import pydantic_model_creator
from ksuid import ksuid # Changed from pyksuid.KsuidMS to ksuid.ksuid

def generate_ksuid():
    return str(ksuid.Ksuid())

class TimestampMixin(models.Model):
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        abstract = True

class InventoryItem(TimestampMixin):
    id = fields.IntField(primary_key=True)
    public_id = fields.CharField(max_length=27, unique=True, default=generate_ksuid, db_index=True)
    name = fields.CharField(max_length=255)
    quantity = fields.IntField(default=0)
    deleted_at = fields.DatetimeField(null=True, default=None) # For soft delete

    order_items_relation: fields.ReverseRelation["OrderItem"]
    category: fields.ForeignKeyRelation["Category"] = fields.ForeignKeyField(
        "models.Category", related_name="inventory_items", on_delete=fields.SET_NULL, null=True
    )

    def __str__(self):
        return f"{self.name} (Stock: {self.quantity})"

    class Meta:
        table = "inventory_items"

class Category(TimestampMixin):
    id = fields.IntField(primary_key=True)
    public_id = fields.CharField(max_length=27, unique=True, default=generate_ksuid, db_index=True)
    name = fields.CharField(max_length=100, unique=True)
    description = fields.TextField(null=True)

    inventory_items: fields.ReverseRelation["InventoryItem"]

    def __str__(self):
        return self.name

    class Meta:
        table = "categories"

class Order(TimestampMixin):
    id = fields.IntField(primary_key=True) # Internal auto-incrementing ID
    order_id = fields.CharField(max_length=50, unique=True, description="Pattern: <year+0000> e.g. 20250001") # User-facing order ID
    public_id = fields.CharField(max_length=27, unique=True, default=generate_ksuid, db_index=True)

    # Contact and Delivery Information
    contact_name = fields.CharField(max_length=255)
    contact_email = fields.CharField(max_length=255) # Consider adding validation
    delivery_address = fields.TextField()

    status = fields.CharField(max_length=50, default="pending_payment") # Current status of the order
    user: fields.ForeignKeyRelation["User"] = fields.ForeignKeyField(
        "models.User", related_name="orders", on_delete=fields.SET_NULL, null=True
    )

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
    id = fields.IntField(primary_key=True)
    public_id = fields.CharField(max_length=27, unique=True, default=generate_ksuid, db_index=True)
    order: fields.ForeignKeyRelation[Order] = fields.ForeignKeyField(
        "models.Order", related_name="items", on_delete=fields.CASCADE
    )
    item: fields.ForeignKeyRelation[InventoryItem] = fields.ForeignKeyField(
        "models.InventoryItem", related_name="order_items_relation", on_delete=fields.RESTRICT # Prevent deleting inventory item if part of an order
    )
    quantity = fields.IntField()
    price_at_purchase = fields.FloatField() # Price of the item at the time of purchase

    def __str__(self):
        # Ensure item is loaded before accessing its name
        # This might require an await if item is not prefetched
        item_name = self.item.name if hasattr(self.item, 'name') and self.item.name else 'N/A'
        order_id_val = self.order.order_id if hasattr(self.order, 'order_id') and self.order.order_id else 'N/A'
        return f"{self.quantity} x {item_name} for Order {order_id_val}"

    class Meta:
        table = "order_items"
        unique_together = (("order", "item"),) # Ensure an item is not added twice to the same order; update quantity instead


class OrderEvent(models.Model): # No TimestampMixin, occurred_at is specific
    id = fields.IntField(primary_key=True)
    public_id = fields.CharField(max_length=27, unique=True, default=generate_ksuid, db_index=True)
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


# Pydantic model creators are useful for quick generation,
# but custom schemas are defined in schemas.py for more control.
# If needed, you can uncomment and use these, but prefer schemas.py for API contracts.

# InventoryItem_Pydantic = pydantic_model_creator(InventoryItem, name="InventoryItemPydantic")
# InventoryItemIn_Pydantic = pydantic_model_creator(InventoryItem, name="InventoryItemInPydantic", exclude_readonly=True, exclude=("public_id", "deleted_at"))

# Order_Pydantic = pydantic_model_creator(Order, name="OrderPydantic")
# OrderItem_Pydantic = pydantic_model_creator(OrderItem, name="OrderItemPydantic")
# OrderEvent_Pydantic = pydantic_model_creator(OrderEvent, name="OrderEventPydantic")


class User(TimestampMixin):
    id = fields.IntField(primary_key=True)
    public_id = fields.CharField(max_length=27, unique=True, default=generate_ksuid, db_index=True)
    username = fields.CharField(max_length=100, unique=True, db_index=True)
    email = fields.CharField(max_length=255, unique=True, db_index=True)
    hashed_password = fields.CharField(max_length=255)
    role = fields.CharField(max_length=50, default="customer")  # E.g., "customer", "admin"
    is_active = fields.BooleanField(default=True)

    orders: fields.ReverseRelation["Order"]

    def __str__(self):
        return f"{self.username} ({self.role})"

    class Meta:
        table = "users"
