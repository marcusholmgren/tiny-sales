from tortoise import fields, models
from app.common.models import TimestampMixin, generate_ksuid

class User(TimestampMixin):
    id = fields.IntField(primary_key=True)
    public_id = fields.CharField(max_length=27, unique=True, default=generate_ksuid, db_index=True)
    username = fields.CharField(max_length=100, unique=True, db_index=True)
    email = fields.CharField(max_length=255, unique=True, db_index=True)
    hashed_password = fields.CharField(max_length=255)
    role = fields.CharField(max_length=50, default="customer")  # E.g., "customer", "admin"
    is_active = fields.BooleanField(default=True)

    orders: fields.ReverseRelation["app.features.orders.models.Order"]

    def __str__(self):
        return f"{self.username} ({self.role})"

    class Meta:
        table = "users"
