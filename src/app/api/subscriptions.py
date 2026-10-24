from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import NoResultFound

from app.api.dependencies import require_role
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.subscription import (
    SubscriptionCreate,
    SubscriptionRead,
    SubscriptionUpdate,
)
from app.services.subscription import (
    create_subscription as subscription_create,
    delete_subscription as subscription_delete,
    list_subscriptions as subscriptions_read,
    read_subscription as subscription_read,
    update_subscription as subscription_update,
)

router = APIRouter(prefix="/subscriptions", tags=["/subscriptions"])
member = require_role(UserRole.USER, UserRole.ADMIN)


def _owned(subscription, user: User, *, write: bool = False):
    if write and subscription.user_id != user.id:
        raise NoResultFound("Subscription not found")
    if user.role != UserRole.ADMIN and subscription.user_id != user.id:
        raise NoResultFound("Subscription not found")
    return subscription


@router.post("/", response_model=SubscriptionRead, status_code=status.HTTP_201_CREATED)
def create_subscription(
    data: SubscriptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(member),
):
    try:
        created = subscription_create(db, data, current_user.id)
        return subscription_read(db, created.id)
    except IntegrityError as exc:
        if "service_name" in str(exc.orig).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A subscription with this service name already exists",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error",
        ) from exc
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error",
        ) from exc


@router.get("/", response_model=list[SubscriptionRead], status_code=status.HTTP_200_OK)
def read_subscriptions(
    db: Session = Depends(get_db),
    current_user: User = Depends(member),
):
    owner_id = None if current_user.role == UserRole.ADMIN else current_user.id
    try:
        subscriptions = subscriptions_read(db, owner_id)
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error",
        ) from exc
    if not subscriptions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No subscriptions found",
        )
    return subscriptions


@router.get("/{id}", response_model=SubscriptionRead)
def read_subscription(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(member),
):
    try:
        return _owned(subscription_read(db, id), current_user)
    except NoResultFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        ) from exc
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error",
        ) from exc


@router.patch("/", response_model=SubscriptionRead)
def update_subscription(
    data: SubscriptionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(member),
):
    try:
        existing = subscription_read(db, data.id)
        _owned(existing, current_user, write=True)
        updated = subscription_update(db, data)
        return subscription_read(db, updated.id)
    except NoResultFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        ) from exc
    except (IntegrityError, OperationalError) as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error",
        ) from exc


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subscription(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(member),
) -> None:
    try:
        _owned(subscription_read(db, id), current_user, write=True)
        subscription_delete(db, id)
    except NoResultFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        ) from exc
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error",
        ) from exc
