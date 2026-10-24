from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.orm.exc import NoResultFound

from app.models.subscription import Subscription
from app.schemas.subscription import SubscriptionCreate, SubscriptionUpdate


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
