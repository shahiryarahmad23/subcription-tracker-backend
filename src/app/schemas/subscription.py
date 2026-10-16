from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

ServiceName = Literal[
    "Netflix",
    "Spotify",
    "YouTube Premium",
    "Disney+",
    "Steam",
    "Apple TV+",
    "Claude",
    "Cursor",
]

Currency = Literal["USD", "EUR", "GBP", "CAD", "AUD", "JPY", "INR", "PKR"]


class SubscriptionCreate(BaseModel):
    service_name: ServiceName
    service_plan: str
    price: Decimal = Field(gt=0)
    currency: Currency
    subscription_date: datetime
    duration: int = Field(gt=0)


class SubscriptionRead(SubscriptionCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID


class SubscriptionUpdate(BaseModel):
    service_name: ServiceName | None = None
    service_plan: str | None = None
    price: Decimal | None = Field(default=None, gt=0)
    currency: Currency | None = None
    subscription_date: datetime | None = None
    duration: int | None = Field(default=None, gt=0)
