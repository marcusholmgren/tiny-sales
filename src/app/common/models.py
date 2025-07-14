"""Models module for the app.

This module contains the common database models for the application.
It includes a TimestampMixin class that provides created_at and updated_at
fields for models, as well as a utility function for generating KSUIDs
(K-Sortable Unique IDentifiers) which are time-ordered UUIDs."""

from tortoise import fields, models
from ksuid import ksuid  # Assuming ksuid is installed


def generate_ksuid():
    """Generate a K-Sortable Unique IDentifier (KSUID).

    KSUIDs are time-ordered UUIDs that are suitable for distributed systems
    and provide better performance characteristics than traditional UUIDs.
    They are URL-safe, timestamp prefixed, and sortable chronologically.

    Returns:
        str: A string representation of the generated KSUID.
    """
    return str(ksuid.Ksuid())


class TimestampMixin(models.Model):
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        abstract = True
