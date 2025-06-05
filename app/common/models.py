import datetime
from tortoise import fields, models
from ksuid import ksuid # Assuming ksuid is installed

def generate_ksuid():
    return str(ksuid.Ksuid())

class TimestampMixin(models.Model):
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        abstract = True
