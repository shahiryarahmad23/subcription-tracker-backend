from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import NoResultFound

from app.db.session import get_db
from app.schemas.subscription import (
    SubscriptionCreate,
    SubscriptionRead,
    SubscriptionUpdate,
)
from app.services.subscription import (
    create_subscription as subscription_create,
    delete_subscription as subscription_delete,
    read_subscription as subscription_read,
    update_subscription as subscription_update,
)

router = APIRouter(prefix="/subscriptions", tags=["/subscriptions"])


@router.post("/", response_model=SubscriptionRead, status_code=status.HTTP_201_CREATED)
def create_subscription(
    data: SubscriptionCreate,
    db: Session = Depends(get_db),
):
    try:
        return subscription_create(db, data)
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


@router.get("/{id}", response_model=SubscriptionRead)
def read_subscription(id: UUID, db: Session = Depends(get_db)):
    try:
        return subscription_read(db, id)
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
):
    try:
        return subscription_update(db, data)
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
def delete_subscription(id: UUID, db: Session = Depends(get_db)) -> None:
    try:
        subscription_delete(db, id)
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error",
        ) from exc
