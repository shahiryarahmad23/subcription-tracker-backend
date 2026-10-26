from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import NoResultFound

from app.api.dependencies import require_role
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.subscription import (
    SubscriptionCreate,
    SubscriptionPage,
    SubscriptionRead,
    SubscriptionUpdate,
)
from app.services.subscription import (
    ForbiddenSubscriptionCursor,
    InvalidSubscriptionCursor,
    create_subscription as subscription_create,
    delete_subscription as subscription_delete,
    list_my_subscriptions,
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


@router.post(
    "/",
    response_model=SubscriptionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a subscription for the signed-in user",
    description=(
        "Creates one subscription owned by the access token's user. "
        "duration is the length in whole months. price is the charge for that period "
        "in currency. subscription_date is the UTC start time."
    ),
)
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


@router.get(
    "/mine",
    response_model=SubscriptionPage,
    summary="Load the signed-in user's subscriptions",
    description=(
        "Returns one page of subscriptions owned by the access token's user, ordered by id. "
        "Omit cursor for the first page. Pass next_cursor from the previous response to continue. "
        "limit is how many subscriptions to return, from 1 to 100, default 20."
    ),
)
def read_my_subscriptions(
    db: Session = Depends(get_db),
    current_user: User = Depends(member),
    cursor: UUID | None = Query(
        default=None,
        description=(
            "Id of the last subscription from the previous page. "
            "Omit this on the first request."
        ),
    ),
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of subscriptions in this page. Default 20, maximum 100.",
    ),
):
    try:
        items, next_cursor = list_my_subscriptions(
            db, current_user.id, cursor=cursor, limit=limit
        )
    except InvalidSubscriptionCursor as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cursor no longer matches a subscription. Request the first page again without a cursor.",
        ) from exc
    except ForbiddenSubscriptionCursor as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cursor belongs to another user's subscription.",
        ) from exc
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error",
        ) from exc
    if cursor is None and not items:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No subscriptions found",
        )
    return SubscriptionPage(items=items, next_cursor=next_cursor)


@router.get(
    "/",
    response_model=list[SubscriptionRead],
    status_code=status.HTTP_200_OK,
    summary="List subscriptions",
    description=(
        "A user receives only their own subscriptions. An admin receives every subscription, "
        "each including user.id and user.username so the client can see who owns it. "
        "For a paged list of only the signed-in user's subscriptions, use GET /subscriptions/mine."
    ),
)
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


@router.get(
    "/{id}",
    response_model=SubscriptionRead,
    summary="Read one subscription",
    description="id is the subscription UUID. A user can read only their own. An admin can read any.",
)
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


@router.patch(
    "/",
    response_model=SubscriptionRead,
    summary="Update one subscription",
    description=(
        "id is the subscription UUID to change. Send only the fields that should change. "
        "duration, when sent, is the new length in whole months. Only the owner can update."
    ),
)
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


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete one subscription",
    description="id is the subscription UUID. Only the owner can delete it. The response body is empty.",
)
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
