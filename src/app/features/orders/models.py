import datetime
from tortoise import fields, models
from ...common.models import TimestampMixin, generate_ksuid


# Forward references for OrderItem and OrderEvent used in Order
class Order(TimestampMixin):
    id = fields.IntField(primary_key=True)
    order_id = fields.CharField(
        max_length=50, unique=True, description="Pattern: <year+0000> e.g. 20250001"
    )
    public_id = fields.CharField(
        max_length=27, unique=True, default=generate_ksuid, db_index=True
    )

    contact_name = fields.CharField(max_length=255)
    contact_email = fields.CharField(max_length=255)
    delivery_address = fields.TextField()
    status = fields.CharField(max_length=50, default="pending_payment")

    user: fields.ForeignKeyRelation["User"] = fields.ForeignKeyField(
        "models.User", related_name="orders", on_delete=fields.SET_NULL, null=True
    )

    items: fields.ReverseRelation["OrderItem"]  # Local forward reference
    events: fields.ReverseRelation["OrderEvent"]  # Local forward reference

    @classmethod
    async def generate_next_order_id(cls):
        year_str = str(datetime.datetime.now().year)
        last_order = (
            await cls.filter(order_id__startswith=year_str)
            .order_by("-order_id")
            .first()
        )
        if last_order and last_order.order_id.startswith(year_str):
            last_sequence = int(last_order.order_id[len(year_str) :])
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
    public_id = fields.CharField(
        max_length=27, unique=True, default=generate_ksuid, db_index=True
    )

    order: fields.ForeignKeyRelation[Order] = fields.ForeignKeyField(
        "models.Order",
        related_name="items",
        on_delete=fields.CASCADE,  # Refers to local Order model
    )
    item: fields.ForeignKeyRelation["InventoryItem"] = fields.ForeignKeyField(
        "models.InventoryItem",
        related_name="order_items_relation",
        on_delete=fields.RESTRICT,
    )

    quantity = fields.IntField()
    price_at_purchase = fields.FloatField()

    def __str__(self):
        item_name = (
            self.item.name if hasattr(self.item, "name") and self.item.name else "N/A"
        )
        order_id_val = (
            self.order.order_id
            if hasattr(self.order, "order_id") and self.order.order_id
            else "N/A"
        )
        return f"{self.quantity} x {item_name} for Order {order_id_val}"

    class Meta:
        table = "order_items"
        unique_together = (("order", "item"),)


class OrderEvent(models.Model):  # No TimestampMixin
    id = fields.IntField(primary_key=True)
    public_id = fields.CharField(
        max_length=27, unique=True, default=generate_ksuid, db_index=True
    )

    order: fields.ForeignKeyRelation[Order] = fields.ForeignKeyField(
        "models.Order",
        related_name="events",
        on_delete=fields.CASCADE,  # Refers to local Order model
    )

    event_type = fields.CharField(max_length=100)
    data = fields.JSONField(null=True)
    occurred_at = fields.DatetimeField(auto_now_add=True)

    def __str__(self):
        order_id_val = (
            self.order.order_id
            if hasattr(self.order, "order_id") and self.order.order_id
            else "N/A"
        )
        return (
            f"Event '{self.event_type}' for Order {order_id_val} at {self.occurred_at}"
        )

    class Meta:
        table = "order_events"
        ordering = ["occurred_at"]
