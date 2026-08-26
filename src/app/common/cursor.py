"""Utilities and schemas for cursor-based pagination."""

import base64
import json
from typing import Any, Generic, List, Optional, TypeVar
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class CursorPage(BaseModel, Generic[T]):
    """Generic response wrapper for cursor-based pagination."""

    items: List[T] = Field(..., description="List of items for the current page.")
    next_cursor: Optional[str] = Field(
        None, description="Cursor for fetching the next page of results."
    )
    prev_cursor: Optional[str] = Field(
        None, description="Cursor for fetching the previous page of results."
    )
    has_next: bool = Field(
        False, description="Flag indicating if more data exists in the forward direction."
    )
    has_prev: bool = Field(
        False, description="Flag indicating if more data exists in the backward direction."
    )

    model_config = ConfigDict(
        from_attributes=True,
        protected_namespaces=(),
    )


def encode_cursor(data: Any) -> str:
    """Encodes a Python object (e.g. dict or list) into a Base64 string cursor."""
    json_bytes = json.dumps(data, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(json_bytes).decode("utf-8")


def decode_cursor(cursor: str) -> Any:
    """Decodes a Base64 string cursor into a Python object."""
    try:
        json_bytes = base64.urlsafe_b64decode(cursor.encode("utf-8"))
        return json.loads(json_bytes.decode("utf-8"))
    except Exception:
        raise ValueError("Invalid cursor format")
