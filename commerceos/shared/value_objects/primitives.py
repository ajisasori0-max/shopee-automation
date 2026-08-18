from decimal import Decimal
from datetime import date, datetime, timezone
from typing import Optional

from pydantic import BaseModel, ConfigDict


class Money(BaseModel):
    """Immutable money value object."""
    model_config = ConfigDict(frozen=True)

    amount: Decimal
    currency: str = "IDR"

    def __add__(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError("Cannot add Money with different currencies")
        return Money(amount=self.amount + other.amount, currency=self.currency)

    def __sub__(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError("Cannot subtract Money with different currencies")
        return Money(amount=self.amount - other.amount, currency=self.currency)


class Percentage(BaseModel):
    """Percentage value object (stored as decimal, e.g. 0.25 for 25%)."""
    model_config = ConfigDict(frozen=True)

    value: Decimal

    def of(self, amount: Decimal) -> Decimal:
        return amount * self.value


class DateRange(BaseModel):
    """Inclusive date range value object."""
    model_config = ConfigDict(frozen=True)

    start: date
    end: date

    def contains(self, value: date) -> bool:
        return self.start <= value <= self.end

    @property
    def days(self) -> int:
        return (self.end - self.start).days + 1


def utc_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)
