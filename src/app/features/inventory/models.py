"""Data models for inventory management, including Category and InventoryItem."""

from tortoise import fields
from decimal import Decimal

from ...common import Currency, Money
from ..orders.models import OrderItem
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
    price_amount = fields.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=Decimal("0.0000"),
        description="Amount of the current price",
    )
    price_currency = fields.CharField(
        max_length=3,
        default="SEK",
        description="Currency code of the current price",
    )
    deleted_at = fields.DatetimeField(null=True, default=None)  # For soft delete

    def __init__(self, **kwargs):
        current_price = kwargs.pop("current_price", None)
        super().__init__(**kwargs)
        if current_price is not None:
            self.current_price = current_price

    # String forward reference for inter-feature relation
    order_items_relation: fields.ReverseRelation["OrderItem"]

    category: fields.ForeignKeyRelation[Category] = fields.ForeignKeyField(
        "models.Category",
        related_name="inventory_items",
        on_delete=fields.SET_NULL,
        null=True,
    )

    @property
    def current_price(self) -> Money:
        return Money.of(self.price_amount, Currency[self.price_currency])

    @current_price.setter
    def current_price(self, val: Money | float | Decimal):
        if not isinstance(val, Money):
            val = Money.of(val, Currency.SEK)
        self.price_amount = val.amount
        self.price_currency = val.currency.code

    def __str__(self):
        return f"{self.name} (Stock: {self.quantity}, Price: {self.current_price})"

    class Meta:
        table = "inventory_items"


# Resolve forward references if Category was defined after InventoryItem
# However, defining Category first avoids this need for local refs.
# Category.inventory_items: fields.ReverseRelation["InventoryItem"] # This would be if defined after
