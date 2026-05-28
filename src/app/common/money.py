from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal, getcontext
from enum import Enum

getcontext().prec = 28


# --- Valuta ---
class Currency(Enum):
    """Represents a currency with a code and exponent."""

    SEK = ("SEK", 2)
    EUR = ("EUR", 2)
    USD = ("USD", 2)
    JPY = ("JPY", 0)  # yen has no decimals

    def __init__(self, code: str, exponent: int):
        """Initialize a currency with a code and exponent."""

        self.code = code
        self.exponent = exponent

    @property
    def quant(self) -> Decimal:
        """Returns the quantization factor for the currency."""

        return Decimal("1").scaleb(-self.exponent)


def _to_decimal(value) -> Decimal:
    """Converts the value to a Decimal."""

    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


# --- Money value object ---
@dataclass(frozen=True, slots=True)
class Money:
    """Represents a monetary value with a currency."""

    _amount: Decimal
    currency: Currency

    def __post_init__(self):
        """Rounds the amount to the currency's quantization factor."""

        quant = self.currency.quant
        rounded = self._amount.quantize(quant, rounding=ROUND_HALF_EVEN)
        object.__setattr__(self, "_amount", rounded)

    # --- Factory ---
    @classmethod
    def of(cls, amount, currency: Currency) -> "Money":
        """Creates a Money object from an amount and currency."""
        return cls(_to_decimal(amount), currency)

    @classmethod
    def from_minor(cls, minor: int, currency: Currency) -> "Money":
        """Creates a Money object from a minor unit value and currency."""
        factor = Decimal(10) ** currency.exponent
        return cls(Decimal(minor) / factor, currency)

    # --- Presentation ---
    def __str__(self) -> str:
        return f"{self._amount:.{self.currency.exponent}f} {self.currency.code}"

    def __repr__(self) -> str:
        return f"Money(amount={str(self._amount)}, currency='{self.currency.code}')"

    # --- Access ---
    @property
    def amount(self) -> Decimal:
        """Returns the amount of the money."""
        return self._amount

    def to_minor(self) -> int:
        """Converts the amount to a minor unit value."""
        factor = Decimal(10) ** self.currency.exponent
        return int((self._amount * factor).to_integral_value())

    # --- Internal validations ---
    def _assert_same_currency(self, other: "Money"):
        if self.currency != other.currency:
            raise ValueError(
                f"Currency mismatch: {self.currency.code} vs {other.currency.code}"
            )

    # --- Comparisons ---
    def __eq__(self, other) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        return self.currency == other.currency and self._amount == other._amount

    def __lt__(self, other) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        self._assert_same_currency(other)
        return self._amount < other._amount

    def __le__(self, other) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        self._assert_same_currency(other)
        return self._amount <= other._amount

    # --- Arithmetic ---
    def __add__(self, other: "Money") -> "Money":
        if not isinstance(other, Money):
            return NotImplemented
        self._assert_same_currency(other)
        return Money(self._amount + other._amount, self.currency)

    def __sub__(self, other: "Money") -> "Money":
        if not isinstance(other, Money):
            return NotImplemented
        self._assert_same_currency(other)
        return Money(self._amount - other._amount, self.currency)

    def __mul__(self, factor: int | float | Decimal) -> "Money":
        return Money(self._amount * _to_decimal(factor), self.currency)

    def __rmul__(self, factor: int | float | Decimal) -> "Money":
        return self.__mul__(factor)

    def __truediv__(self, divisor: int | float | Decimal) -> "Money":
        return Money(self._amount / _to_decimal(divisor), self.currency)

    # --- Allocation (enterprise use-case) ---
    def allocate(self, ratios: list[int]) -> list["Money"]:
        """Allocates the money according to the given ratios."""

        total = sum(ratios)
        quant = self.currency.quant

        remainder = self._amount
        results = []

        for r in ratios:
            part = (self._amount * Decimal(r) / Decimal(total)).quantize(
                quant, rounding=ROUND_HALF_EVEN
            )
            results.append(Money(part, self.currency))
            remainder -= part

        # distribute remainder (minor unit)
        increment = quant
        for i in range(int((remainder / quant).to_integral_value())):
            results[i] = Money(results[i]._amount + increment, self.currency)

        return results

    def convert(self, rate: Decimal, target: Currency) -> "Money":
        """Convert this money to a different currency using the given rate."""
        return Money(self._amount * rate, target)

    def to_dict(self):
        """Convert this money to a dictionary."""
        return {"amount": str(self._amount), "currency": self.currency.code}
