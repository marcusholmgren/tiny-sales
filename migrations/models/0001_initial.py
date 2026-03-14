from tortoise import migrations
from tortoise.migrations import operations as ops
import functools
from app.common.models import generate_ksuid
from json import dumps, loads
from tortoise.fields.base import OnDelete
from tortoise import fields

class Migration(migrations.Migration):
    initial = True

    operations = [
        ops.CreateModel(
            name='Category',
            fields=[
                ('created_at', fields.DatetimeField(auto_now=False, auto_now_add=True)),
                ('updated_at', fields.DatetimeField(auto_now=True, auto_now_add=False)),
                ('id', fields.IntField(generated=True, primary_key=True, unique=True, db_index=True)),
                ('public_id', fields.CharField(default=generate_ksuid, unique=True, db_index=True, max_length=27)),
                ('name', fields.CharField(unique=True, max_length=100)),
                ('description', fields.TextField(null=True, unique=False)),
            ],
            options={'table': 'categories', 'app': 'models', 'pk_attr': 'id'},
            bases=['TimestampMixin'],
        ),
        ops.CreateModel(
            name='InventoryItem',
            fields=[
                ('created_at', fields.DatetimeField(auto_now=False, auto_now_add=True)),
                ('updated_at', fields.DatetimeField(auto_now=True, auto_now_add=False)),
                ('id', fields.IntField(generated=True, primary_key=True, unique=True, db_index=True)),
                ('public_id', fields.CharField(default=generate_ksuid, unique=True, db_index=True, max_length=27)),
                ('name', fields.CharField(max_length=255)),
                ('quantity', fields.IntField(default=0)),
                ('current_price', fields.FloatField(default=0.0, description='Current price of the inventory item')),
                ('deleted_at', fields.DatetimeField(null=True, auto_now=False, auto_now_add=False)),
                ('category', fields.ForeignKeyField('models.Category', source_field='category_id', null=True, db_constraint=True, to_field='id', related_name='inventory_items', on_delete=OnDelete.SET_NULL)),
            ],
            options={'table': 'inventory_items', 'app': 'models', 'pk_attr': 'id'},
            bases=['TimestampMixin'],
        ),
        ops.CreateModel(
            name='User',
            fields=[
                ('created_at', fields.DatetimeField(auto_now=False, auto_now_add=True)),
                ('updated_at', fields.DatetimeField(auto_now=True, auto_now_add=False)),
                ('id', fields.IntField(generated=True, primary_key=True, unique=True, db_index=True)),
                ('public_id', fields.CharField(default=generate_ksuid, unique=True, db_index=True, max_length=27)),
                ('username', fields.CharField(unique=True, db_index=True, max_length=100)),
                ('email', fields.CharField(unique=True, db_index=True, max_length=255)),
                ('hashed_password', fields.CharField(max_length=255)),
                ('role', fields.CharField(default='customer', max_length=50)),
                ('is_active', fields.BooleanField(default=True)),
            ],
            options={'table': 'users', 'app': 'models', 'pk_attr': 'id'},
            bases=['TimestampMixin'],
        ),
        ops.CreateModel(
            name='Order',
            fields=[
                ('created_at', fields.DatetimeField(auto_now=False, auto_now_add=True)),
                ('updated_at', fields.DatetimeField(auto_now=True, auto_now_add=False)),
                ('id', fields.IntField(generated=True, primary_key=True, unique=True, db_index=True)),
                ('order_id', fields.CharField(unique=True, description='Pattern: <year+0000> e.g. 20250001', max_length=50)),
                ('public_id', fields.CharField(default=generate_ksuid, unique=True, db_index=True, max_length=27)),
                ('contact_name', fields.CharField(max_length=255)),
                ('contact_email', fields.CharField(max_length=255)),
                ('delivery_address', fields.TextField(unique=False)),
                ('status', fields.CharField(default='pending_payment', max_length=50)),
                ('user', fields.ForeignKeyField('models.User', source_field='user_id', null=True, db_constraint=True, to_field='id', related_name='orders', on_delete=OnDelete.SET_NULL)),
            ],
            options={'table': 'orders', 'app': 'models', 'pk_attr': 'id'},
            bases=['TimestampMixin'],
        ),
        ops.CreateModel(
            name='OrderEvent',
            fields=[
                ('id', fields.IntField(generated=True, primary_key=True, unique=True, db_index=True)),
                ('public_id', fields.CharField(default=generate_ksuid, unique=True, db_index=True, max_length=27)),
                ('order', fields.ForeignKeyField('models.Order', source_field='order_id', db_constraint=True, to_field='id', related_name='events', on_delete=OnDelete.CASCADE)),
                ('event_type', fields.CharField(max_length=100)),
                ('data', fields.JSONField(null=True, encoder=functools.partial(dumps, separators=(',', ':')), decoder=loads)),
                ('occurred_at', fields.DatetimeField(auto_now=False, auto_now_add=True)),
            ],
            options={'table': 'order_events', 'app': 'models', 'pk_attr': 'id'},
            bases=['Model'],
        ),
        ops.CreateModel(
            name='OrderItem',
            fields=[
                ('created_at', fields.DatetimeField(auto_now=False, auto_now_add=True)),
                ('updated_at', fields.DatetimeField(auto_now=True, auto_now_add=False)),
                ('id', fields.IntField(generated=True, primary_key=True, unique=True, db_index=True)),
                ('public_id', fields.CharField(default=generate_ksuid, unique=True, db_index=True, max_length=27)),
                ('order', fields.ForeignKeyField('models.Order', source_field='order_id', db_constraint=True, to_field='id', related_name='items', on_delete=OnDelete.CASCADE)),
                ('item', fields.ForeignKeyField('models.InventoryItem', source_field='item_id', db_constraint=True, to_field='id', related_name='order_items_relation', on_delete=OnDelete.RESTRICT)),
                ('quantity', fields.IntField()),
                ('price_at_purchase', fields.FloatField()),
            ],
            options={'table': 'order_items', 'app': 'models', 'unique_together': (('order', 'item'),), 'pk_attr': 'id'},
            bases=['TimestampMixin'],
        ),
    ]
