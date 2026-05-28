from decimal import Decimal

import pytest

from app.common import Currency, Money


def test_creation():
    m = Money.of("10.00", Currency.SEK)
    assert m.amount == Decimal("10.00")
    assert m.currency == Currency.SEK


def test_minor_units():
    m = Money.from_minor(1234, Currency.SEK)
    assert m.amount == Decimal("12.34")
    assert m.to_minor() == 1234


def test_rounding_bankers():
    m = Money.of("2.345", Currency.SEK)
    assert m.amount == Decimal("2.34")

    m = Money.of("2.355", Currency.SEK)
    assert m.amount == Decimal("2.36")


def test_add_same_currency():
    a = Money.of("1.00", Currency.SEK)
    b = Money.of("2.00", Currency.SEK)
    assert a + b == Money.of("3.00", Currency.SEK)


def test_add_currency_mismatch():
    a = Money.of("1.00", Currency.SEK)
    b = Money.of("1.00", Currency.EUR)

    with pytest.raises(ValueError):
        _ = a + b


def test_comparison():
    a = Money.of("1.00", Currency.SEK)
    b = Money.of("2.00", Currency.SEK)
    assert a < b


def test_mul_div():
    m = Money.of("10.00", Currency.SEK)
    assert m * 2 == Money.of("20.00", Currency.SEK)
    assert m / 2 == Money.of("5.00", Currency.SEK)


def test_allocation():
    m = Money.of("10.00", Currency.SEK)
    parts = m.allocate([1, 1, 1])

    print(f"{parts=}")
    assert sum(p.amount for p in parts) == m.amount
    assert all(p.currency == Currency.SEK for p in parts)


def test_jpy_no_decimals():
    m = Money.of(100.6, Currency.JPY)
    assert m.amount == Decimal("101")  # bank rounding
