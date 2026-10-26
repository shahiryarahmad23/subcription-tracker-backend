from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.orm.exc import NoResultFound

from app.models.subscription import Subscription
from app.schemas.subscription import SubscriptionCreate, SubscriptionUpdate


class InvalidSubscriptionCursor(Exception):
    """The cursor no longer matches a subscription row."""


class ForbiddenSubscriptionCursor(Exception):
    """The cursor belongs to another user's subscription."""


def create_subscription(
    db: Session, data: SubscriptionCreate, user_id: UUID
) -> Subscription:
    subscription = Subscription(**data.model_dump(), user_id=user_id)
    try:
        db.add(subscription)
        db.commit()
        db.refresh(subscription)
    except (IntegrityError, OperationalError):
        db.rollback()
        raise
    return subscription


def read_subscription(db: Session, id: UUID) -> Subscription:
    statement = (
        select(Subscription)
        .options(joinedload(Subscription.user))
        .where(Subscription.id == id)
    )
    try:
        subscription = db.scalar(statement)
    except OperationalError:
        raise
    if subscription is None:
        raise NoResultFound("Subscription not found")
    return subscription


def list_subscriptions(
    db: Session, user_id: UUID | None = None
) -> list[Subscription]:
    statement = select(Subscription).options(joinedload(Subscription.user))
    if user_id is not None:
        statement = statement.where(Subscription.user_id == user_id)
    try:
        return list(db.scalars(statement).unique())
    except OperationalError:
        raise


def list_my_subscriptions(
    db: Session,
    user_id: UUID,
    *,
    cursor: UUID | None = None,
    limit: int = 20,
) -> tuple[list[Subscription], UUID | None]:
    if cursor is not None:
        anchor = db.get(Subscription, cursor)
        if anchor is None:
            raise InvalidSubscriptionCursor
        if anchor.user_id != user_id:
            raise ForbiddenSubscriptionCursor

    statement = (
        select(Subscription)
        .options(joinedload(Subscription.user))
        .where(Subscription.user_id == user_id)
        .order_by(Subscription.id)
    )
    if cursor is not None:
        statement = statement.where(Subscription.id > cursor)
    try:
        rows = list(db.scalars(statement.limit(limit + 1)).unique())
    except OperationalError:
        raise
    has_more = len(rows) > limit
    page = rows[:limit]
    next_cursor = page[-1].id if has_more and page else None
    return page, next_cursor


def update_subscription(db: Session, data: SubscriptionUpdate) -> Subscription:
    subscription = read_subscription(db, data.id)
    for field, value in data.model_dump(exclude_unset=True, exclude={"id"}).items():
        setattr(subscription, field, value)
    try:
        db.commit()
        db.refresh(subscription)
    except (IntegrityError, OperationalError):
        db.rollback()
        raise
    return subscription


def delete_subscription(db: Session, id: UUID) -> None:
    try:
        subscription = db.get(Subscription, id)
        if subscription is None:
            return
        db.delete(subscription)
        db.commit()
    except OperationalError:
        db.rollback()
        raise
