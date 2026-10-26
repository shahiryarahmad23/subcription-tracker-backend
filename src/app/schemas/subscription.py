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

_SERVICE_NAME = (
    "Which service this subscription is for. One of: Netflix, Spotify, "
    "YouTube Premium, Disney+, Steam, Apple TV+, Claude, Cursor. "
    "Each service name can exist only once in the whole database."
)
_SERVICE_PLAN = (
    "The plan name at that service, such as Premium, Individual, Family, or Annual. "
    "This is free text supplied by the client."
)
_PRICE = (
    "Amount charged for one billing period in the selected currency. "
    "Must be greater than 0. Use up to 2 decimal places, for example 15.99."
)
_CURRENCY = (
    "ISO currency code for price. One of: USD, EUR, GBP, CAD, AUD, JPY, INR, PKR."
)
_SUBSCRIPTION_DATE = (
    "UTC date and time when the subscription started, in ISO 8601 format, "
    "for example 2026-01-15T00:00:00Z."
)
_DURATION = (
    "How long the subscription lasts, as a whole number of months. "
    "Must be greater than 0. For example, 12 means one year."
)


class SubscriptionCreate(BaseModel):
    service_name: ServiceName = Field(description=_SERVICE_NAME)
    service_plan: str = Field(description=_SERVICE_PLAN, examples=["Premium"])
    price: Decimal = Field(gt=0, description=_PRICE, examples=["15.99"])
    currency: Currency = Field(description=_CURRENCY)
    subscription_date: datetime = Field(description=_SUBSCRIPTION_DATE)
    duration: int = Field(gt=0, description=_DURATION, examples=[12])


class SubscriptionOwner(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(description="UUID of the user who owns this subscription.")
    username: str = Field(description="Login name of the user who owns this subscription.")


class SubscriptionRead(SubscriptionCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(description="UUID of this subscription. Use it to read, update, or delete.")
    user_id: UUID = Field(description="UUID of the owner. Taken from the access token on create.")
    user: SubscriptionOwner = Field(description="Owner id and username.")
    created_at: datetime = Field(description="UTC time when this subscription was saved.")


class SubscriptionUpdate(BaseModel):
    id: UUID = Field(description="UUID of the subscription to change. Only the owner can update it.")
    service_name: ServiceName | None = Field(default=None, description=_SERVICE_NAME)
    service_plan: str | None = Field(default=None, description=_SERVICE_PLAN)
    price: Decimal | None = Field(default=None, gt=0, description=_PRICE)
    currency: Currency | None = Field(default=None, description=_CURRENCY)
    subscription_date: datetime | None = Field(default=None, description=_SUBSCRIPTION_DATE)
    duration: int | None = Field(default=None, gt=0, description=_DURATION)


class SubscriptionPage(BaseModel):
    items: list[SubscriptionRead] = Field(
        description="This page of the signed-in user's subscriptions, ordered by id."
    )
    next_cursor: UUID | None = Field(
        description=(
            "Send this value as the cursor query parameter to load the next page. "
            "Null means this is the last page."
        )
    )
