"""Pydantic schemas for authentication, defining the structure for request and response data."""

from pydantic import BaseModel, ConfigDict, Field, EmailStr
from typing import Optional
import datetime


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=100, description="Username")
    email: EmailStr = Field(..., description="User email address")


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, description="User password")


class UserResponse(UserBase):
    public_id: str = Field(
        ..., description="Public unique identifier for the user (KSUID)"
    )
    role: str = Field(..., description="User role (e.g., customer, admin)")
    is_active: bool = Field(..., description="Whether the user account is active")
    created_at: datetime.datetime = Field(
        ..., description="Timestamp of when the user was created"
    )
    updated_at: datetime.datetime = Field(
        ..., description="Timestamp of when the user was last updated"
    )

    model_config = ConfigDict(
        from_attributes=True,
        protected_namespaces=(),
    )


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    sub: Optional[str] = None
