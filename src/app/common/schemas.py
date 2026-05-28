from decimal import Decimal
from typing import Any
from pydantic import BaseModel, Field, model_validator


class MoneySchema(BaseModel):
    """Pydantic schema representing a monetary value."""

    amount: Decimal = Field(
        ...,
        description="The exact decimal amount of the monetary value.",
        examples=["10.50", "99.99"],
    )
    currency: str = Field(
        default="SEK",
        description="Three-letter ISO currency code (e.g., SEK, USD, EUR, JPY).",
        min_length=3,
        max_length=3,
        examples=["SEK", "USD"],
    )

    @model_validator(mode="before")
    @classmethod
    def coerce_money(cls, data: Any) -> Any:
        if isinstance(data, (int, float, Decimal, str)):
            return {"amount": Decimal(str(data)), "currency": "SEK"}
        elif isinstance(data, dict):
            # Allow strings, floats, ints, or Decimals for amount in dictionary inputs
            if "amount" in data and isinstance(data["amount"], (int, float, Decimal, str)):
                data = data.copy()
                data["amount"] = Decimal(str(data["amount"]))
            if "currency" not in data:
                data = data.copy()
                data["currency"] = "SEK"
        return data
