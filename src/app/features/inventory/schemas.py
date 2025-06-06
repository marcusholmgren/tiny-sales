from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional
import datetime

# --- Category Schemas (defined first as InventoryItemResponse uses CategoryResponse) ---
class CategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Name of the category")
    description: Optional[str] = Field(None, max_length=500, description="Optional description for the category")

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="New name of the category")
    description: Optional[str] = Field(None, max_length=500, description="New description for the category")

class CategoryResponse(CategoryBase):
    public_id: str = Field(..., description="Public unique identifier for the category (KSUID)")
    created_at: datetime.datetime = Field(..., description="Timestamp of when the category was created")
    updated_at: datetime.datetime = Field(..., description="Timestamp of when the category was last updated")

    model_config = ConfigDict(
        from_attributes=True,
        protected_namespaces=(),
    )

# --- Inventory Schemas ---
class InventoryItemBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Name of the inventory item")
    quantity: int = Field(default=0, ge=0, description="Current stock quantity of the item")
    current_price: float = Field(default=0.0, ge=0, description="Current price of the item")

class InventoryItemCreate(InventoryItemBase):
    category_id: Optional[str] = Field(None, description="Public ID of the category to assign to the item")

class InventoryItemUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="New name of the inventory item")
    quantity: Optional[int] = Field(None, ge=0, description="New stock quantity of the item")
    current_price: Optional[float] = Field(None, ge=0, description="New current price of the item")
    category_id: Optional[str] = Field(None, description="Public ID of the new category to assign to the item")

class InventoryItemResponse(InventoryItemBase):
    public_id: str = Field(..., description="Public unique identifier for the item (KSUID)")
    category: Optional[CategoryResponse] = Field(None, description="Category of the inventory item")
    created_at: datetime.datetime = Field(..., description="Timestamp of when the item was created")
    updated_at: datetime.datetime = Field(..., description="Timestamp of when the item was last updated")

    model_config = ConfigDict(
        from_attributes=True,
        protected_namespaces=(),
    )

class PaginatedInventoryResponse(BaseModel):
    items: list[InventoryItemResponse]
    total: int
    page: int
    size: int

    model_config = ConfigDict(
        from_attributes=True,
        protected_namespaces=(),
    )
