from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, OperationalError

from app.models.user import User
from app.schemas.subscription import SubscriptionCreate
from app.services.subscription import create_subscription


def subscription_data(user_id: UUID, service_name: str = "Netflix") -> SubscriptionCreate:
    return SubscriptionCreate(
        user_id=user_id,
        service_name=service_name,
        service_plan="Premium",
        price=Decimal("15.99"),
        currency="USD",
        subscription_date=datetime(2026, 1, 15, tzinfo=timezone.utc),
        duration=12,
    )


def test_create_subscription_persists_required_fields(db_session, user):
    created = create_subscription(db_session, subscription_data(user.id))

    assert created.id is not None
    assert created.user_id == user.id
    assert isinstance(created.user_id, UUID)
    assert created.service_name == "Netflix"
    assert created.service_plan == "Premium"
    assert created.price == Decimal("15.99")
    assert created.currency == "USD"
    assert created.subscription_date == datetime(2026, 1, 15, tzinfo=timezone.utc)
    assert created.duration == 12
    assert created.created_at is not None
    assert created.updated_at is not None
    assert created.user.id == user.id
    assert created.user.username == user.username
    assert created.user.email == user.email


def test_create_subscription_coerces_user_id_string(db_session, user):
    data = SubscriptionCreate.model_validate(
        {
            "user_id": str(user.id),
            "service_name": "Spotify",
            "service_plan": "Individual",
            "price": "9.99",
            "currency": "EUR",
            "subscription_date": "2026-02-01T00:00:00Z",
            "duration": 1,
        }
    )

    created = create_subscription(db_session, data)

    assert created.user_id == user.id
    assert isinstance(created.user_id, UUID)


def test_create_subscription_allows_two_services_for_one_user(db_session, user):
    first = create_subscription(db_session, subscription_data(user.id, "Netflix"))
    second = create_subscription(db_session, subscription_data(user.id, "Steam"))

    assert first.user_id == second.user_id == user.id
    assert {first.service_name, second.service_name} == {"Netflix", "Steam"}


def test_create_subscription_rejects_missing_required_fields():
    with pytest.raises(ValidationError):
        SubscriptionCreate(
            user_id=uuid4(),
            service_name="Netflix",
            price=Decimal("10.00"),
            currency="USD",
            subscription_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
            duration=1,
        )


def test_create_subscription_rejects_null_required_column(db_session, user):
    data = SubscriptionCreate.model_construct(
        user_id=user.id,
        service_name="Disney+",
        service_plan=None,
        price=Decimal("10.00"),
        currency="USD",
        subscription_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
        duration=1,
    )

    with pytest.raises(IntegrityError):
        create_subscription(db_session, data)

    db_session.rollback()


def test_create_subscription_rejects_duplicate_service_name(db_session, user):
    create_subscription(db_session, subscription_data(user.id, "Cursor"))
    other = User(
        username="other",
        hashed_password="secret",
        email="other@example.com",
        dob=date(1999, 5, 5),
    )
    db_session.add(other)
    db_session.commit()

    with pytest.raises(IntegrityError):
        create_subscription(db_session, subscription_data(other.id, "Cursor"))

    db_session.rollback()


def test_create_subscription_rejects_unknown_user(db_session):
    with pytest.raises(IntegrityError):
        create_subscription(db_session, subscription_data(uuid4(), "Claude"))

    db_session.rollback()


def test_create_subscription_rejects_invalid_user_id():
    data = SubscriptionCreate.model_construct(
        user_id="not-a-uuid",
        service_name="Apple TV+",
        service_plan="Monthly",
        price=Decimal("6.99"),
        currency="GBP",
        subscription_date=datetime(2026, 3, 1, tzinfo=timezone.utc),
        duration=3,
    )

    with pytest.raises(ValueError):
        create_subscription(MagicMock(), data)


def test_create_subscription_rolls_back_when_database_connection_fails():
    db = MagicMock()
    db.commit.side_effect = OperationalError("INSERT", {}, Exception("connection refused"))

    with pytest.raises(OperationalError):
        create_subscription(db, subscription_data(uuid4(), "YouTube Premium"))

    db.rollback.assert_called_once()
