from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_role
from app.core.security import create_access_token
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.user import LogoutRequest, TokenPair, UserAccessUpdate, UserCreate, UserLogin, UserRead
from app.services.auth import (
    InvalidRefreshToken,
    RefreshTokenReuse,
    end_refresh_session,
    start_refresh_session,
)
from app.services.subscription import list_subscriptions
from app.services.user import (
    AccountStopped,
    EmailAlreadyExists,
    InvalidCredentials,
    UserNotFound,
    UsernameAlreadyExists,
    delete_user_account,
    list_users,
    login_user,
    register_user,
    set_user_access,
)
from app.schemas.subscription import SubscriptionRead

router = APIRouter(prefix="/user", tags=["/user"])


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register an account",
    description=(
        "username is the unique login name. password is plain text and is stored only as a hash. "
        "email must be unique. dob is the date of birth as YYYY-MM-DD. "
        "Omit role, or send user, to create a normal account. Send admin to create an admin."
    ),
)
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


@router.post(
    "/login",
    response_model=TokenPair,
    summary="Log in",
    description=(
        "username and password are the same values used at registration. "
        "access_token is a JWT to send as Authorization: Bearer. It expires in 15 minutes. "
        "refresh_token is an opaque string to send only to logout."
    ),
)
def login(data: UserLogin, db: Session = Depends(get_db)):
    try:
        user = login_user(db, data)
        refresh_token = start_refresh_session(db, user.id)
    except InvalidCredentials as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        ) from exc
    except AccountStopped as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is stopped",
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


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Log out",
    description=(
        "Requires the bearer access token. refresh_token is the opaque token from login. "
        "This revokes that refresh session. The response body is empty."
    ),
)
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
    summary="List all users",
    description="Admin only. Each item includes id, username, email, and role (user or admin).",
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
    summary="List one user's subscriptions",
    description=(
        "Admin only. user_id is the UUID of the account whose subscriptions to load. "
        "Each subscription includes user.username so the client can see whose it is."
    ),
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


@router.patch(
    "/{user_id}/access",
    response_model=UserRead,
    summary="Stop or restore an account",
    description=(
        "Admin only. active false stops the account from signing in and revokes its refresh tokens. "
        "active true restores it. An admin cannot change their own access."
    ),
)
def update_user_access(
    user_id: UUID,
    data: UserAccessUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You cannot change your own access",
        )
    try:
        return set_user_access(db, user_id, data.active)
    except UserNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        ) from exc
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error",
        ) from exc


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a user",
    description=(
        "Admin only. Deletes the account, its refresh tokens, and its subscriptions. "
        "An admin cannot delete their own account."
    ),
)
def delete_user_route(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> None:
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You cannot delete your own account",
        )
    try:
        delete_user_account(db, user_id)
    except UserNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        ) from exc
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error",
        ) from exc
