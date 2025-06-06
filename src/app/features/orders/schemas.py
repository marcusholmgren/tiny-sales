from pydantic import BaseModel, ConfigDict, Field, EmailStr
from typing import List, Optional, Any
import datetime

# Import UserResponse from auth feature for OrderPublicSchema
from ..auth.schemas import UserResponse

# Schemas for Order Updates (PATCH requests)
class OrderShipRequestSchema(BaseModel):
    tracking_number: Optional[str] = Field(None, description="Tracking number for the shipment")
    shipping_provider: Optional[str] = Field(None, description="Shipping provider for the shipment")

class OrderCancelRequestSchema(BaseModel):
    reason: Optional[str] = Field(None, description="Reason for cancelling the order")

# Order Item Schemas
class OrderItemBase(BaseModel):
    product_public_id: str = Field(..., description="Public KSUID of the product (InventoryItem)")
    quantity: int = Field(..., gt=0, description="Quantity of the product")

class OrderItemCreateSchema(OrderItemBase):
    price_at_purchase: float = Field(..., gt=0, description="Price of the product at the time of purchase")

class OrderItemPublicSchema(OrderItemBase):
    public_id: str = Field(..., description="Public KSUID of this order item")
    price_at_purchase: float = Field(..., description="Price of the product at the time of purchase")
    # product_name: Optional[str] = None # Consider adding this if needed for display, requires fetching item details

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

# Order Event Schemas
class OrderEventPublicSchema(BaseModel):
    public_id: str = Field(..., description="Public KSUID of the event")
    event_type: str = Field(..., description="Type of the order event")
    data: Optional[dict[str, Any]] = Field(None, description="Additional data associated with the event")
    occurred_at: datetime.datetime = Field(..., description="Timestamp of when the event occurred")

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

# Order Schemas
class OrderBase(BaseModel):
    contact_name: str = Field(..., max_length=255)
    contact_email: EmailStr
    delivery_address: str

class OrderCreateSchema(OrderBase):
    items: List[OrderItemCreateSchema] = Field(..., min_length=1)

class OrderPublicSchema(OrderBase):
    public_id: str
    order_id: str
    user: Optional[UserResponse] = None # User can be None based on model (SET_NULL)
    status: str
    items: List[OrderItemPublicSchema]
    events: List[OrderEventPublicSchema]
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

# If forward refs were an issue (UserResponse defined after OrderPublicSchema), rebuild would be needed.
# OrderPublicSchema.model_rebuild()
