from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_role
from app.core.security import create_access_token
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.user import LogoutRequest, TokenPair, UserCreate, UserLogin, UserRead
from app.services.auth import (
    InvalidRefreshToken,
    RefreshTokenReuse,
    end_refresh_session,
    start_refresh_session,
)
from app.services.subscription import list_subscriptions
from app.services.user import (
    EmailAlreadyExists,
    InvalidCredentials,
    UsernameAlreadyExists,
    list_users,
    login_user,
    register_user,
)
from app.schemas.subscription import SubscriptionRead

router = APIRouter(prefix="/user", tags=["/user"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register_user_route(data: UserCreate, db: Session = Depends(get_db)):
    try:
        return register_user(db, data)
    except UsernameAlreadyExists as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists",
        ) from exc
    except EmailAlreadyExists as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already exists",
        ) from exc
    except (IntegrityError, OperationalError) as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error",
        ) from exc


@router.post("/login", response_model=TokenPair)
def login(data: UserLogin, db: Session = Depends(get_db)):
    try:
        user = login_user(db, data)
        refresh_token = start_refresh_session(db, user.id)
    except InvalidCredentials as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        ) from exc
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error",
        ) from exc
    return TokenPair(
        access_token=create_access_token(str(user.id)),
        refresh_token=refresh_token,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    data: LogoutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    try:
        end_refresh_session(db, data.refresh_token, current_user.id)
    except (InvalidRefreshToken, RefreshTokenReuse) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        ) from exc
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error",
        ) from exc


@router.get(
    "/",
    response_model=list[UserRead],
    status_code=status.HTTP_200_OK,
)
def read_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN)),
):
    try:
        users = list_users(db)
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error",
        ) from exc
    if not users:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No users found",
        )
    return users


@router.get(
    "/{user_id}/subscriptions",
    response_model=list[SubscriptionRead],
)
def read_user_subscriptions(
    user_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN)),
):
    try:
        subscriptions = list_subscriptions(db, user_id)
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
