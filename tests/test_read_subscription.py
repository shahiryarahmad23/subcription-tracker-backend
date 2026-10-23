from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm.exc import NoResultFound

from app.services.subscription import create_subscription, read_subscription
from tests.test_create_subscription import subscription_data


def test_read_subscription_returns_stored_row(db_session, user):
    created = create_subscription(db_session, subscription_data(user.id))

    found = read_subscription(db_session, created.id)

    assert found.id == created.id
    assert found.user_id == user.id
    assert found.service_name == "Netflix"
    assert found.service_plan == "Premium"
    assert found.price == created.price
    assert found.currency == "USD"
    assert found.subscription_date == created.subscription_date
    assert found.duration == 12


def test_read_subscription_returns_only_the_requested_row(db_session, user):
    netflix = create_subscription(db_session, subscription_data(user.id, "Netflix"))
    steam = create_subscription(db_session, subscription_data(user.id, "Steam"))

    assert read_subscription(db_session, netflix.id).service_name == "Netflix"
    assert read_subscription(db_session, steam.id).service_name == "Steam"


def test_read_subscription_raises_when_id_does_not_exist(db_session):
    missing_id = uuid4()

    with pytest.raises(NoResultFound, match="Subscription not found"):
        read_subscription(db_session, missing_id)


def test_read_subscription_raises_after_row_is_deleted(db_session, user):
    created = create_subscription(db_session, subscription_data(user.id))
    db_session.delete(created)
    db_session.commit()

    with pytest.raises(NoResultFound, match="Subscription not found"):
        read_subscription(db_session, created.id)


def test_read_subscription_reraises_database_connection_failure():
    db = MagicMock()
    db.get.side_effect = OperationalError("SELECT", {}, Exception("connection refused"))

    with pytest.raises(OperationalError):
        read_subscription(db, uuid4())

    db.rollback.assert_not_called()


def test_read_subscription_returns_same_object_for_same_id(db_session, user):
    created = create_subscription(db_session, subscription_data(user.id))

    first = read_subscription(db_session, created.id)
    second = read_subscription(db_session, created.id)

    assert first is second
