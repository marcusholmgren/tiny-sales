"""Data models for inventory management, including Category and InventoryItem."""

from tortoise import fields
from ...common.models import TimestampMixin, generate_ksuid


# Forward reference for Category used in InventoryItem
class Category(TimestampMixin):
    id = fields.IntField(primary_key=True)
    public_id = fields.CharField(
        max_length=27, unique=True, default=generate_ksuid, db_index=True
    )
    name = fields.CharField(max_length=100, unique=True)
    description = fields.TextField(null=True)

    inventory_items: fields.ReverseRelation[
        "InventoryItem"
    ]  # Forward reference to InventoryItem

    def __str__(self):
        return self.name

    class Meta:
        table = "categories"


class InventoryItem(TimestampMixin):
    id = fields.IntField(primary_key=True)
    public_id = fields.CharField(
        max_length=27, unique=True, default=generate_ksuid, db_index=True
    )
    name = fields.CharField(max_length=255)
    quantity = fields.IntField(default=0)
    current_price = fields.FloatField(
        default=0.0, description="Current price of the inventory item"
    )
    deleted_at = fields.DatetimeField(null=True, default=None)  # For soft delete

    # String forward reference for inter-feature relation
    order_items_relation: fields.ReverseRelation["OrderItem"]

    category: fields.ForeignKeyRelation[Category] = fields.ForeignKeyField(
        "models.Category",
        related_name="inventory_items",
        on_delete=fields.SET_NULL,
        null=True,
    )

    def __str__(self):
        return f"{self.name} (Stock: {self.quantity}, Price: ${self.current_price:.2f})"

    class Meta:
        table = "inventory_items"


# Resolve forward references if Category was defined after InventoryItem
# However, defining Category first avoids this need for local refs.
# Category.inventory_items: fields.ReverseRelation["InventoryItem"] # This would be if defined after
