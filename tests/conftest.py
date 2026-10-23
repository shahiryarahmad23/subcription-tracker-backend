import os
from collections.abc import Generator
from datetime import date

import pytest
from sqlalchemy import URL, create_engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User

test_engine = create_engine(
    URL.create(
        "postgresql+psycopg",
        username=settings.postgres_user,
        password=settings.postgres_password,
        host=settings.postgres_host,
        port=int(os.environ.get("TEST_POSTGRES_PORT", "5433")),
        database=os.environ.get("TEST_POSTGRES_DB", "subscriptiondb_test"),
    ),
    pool_pre_ping=True,
)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    connection = test_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def user(db_session: Session) -> User:
    account = User(
        username="reader",
        hashed_password="secret",
        email="reader@example.com",
        dob=date(2000, 1, 1),
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account
