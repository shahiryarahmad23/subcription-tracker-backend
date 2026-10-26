from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.core.security import TokenError, decode_access_token, hash_password, verify_password
from app.models.refresh_token import RefreshToken
from app.models.subscription import Subscription
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserLogin


class UsernameAlreadyExists(Exception):
    pass


class EmailAlreadyExists(Exception):
    pass


class InvalidCredentials(Exception):
    pass


class NotAuthenticated(Exception):
    pass


class NotAuthorized(Exception):
    pass


class UserNotFound(Exception):
    pass


class AccountStopped(Exception):
    pass


def register_user(db: Session, data: UserCreate) -> User:
    payload = data.model_dump(exclude_unset=True)
    payload["hashed_password"] = hash_password(payload.pop("password"))
    if payload.get("role") is None:
        payload.pop("role", None)
    user = User(**payload)
    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except IntegrityError as exc:
        db.rollback()
        message = str(exc.orig).lower()
        if "username" in message:
            raise UsernameAlreadyExists from exc
        if "email" in message:
            raise EmailAlreadyExists from exc
        raise
    except OperationalError:
        db.rollback()
        raise
    return user


def login_user(db: Session, data: UserLogin) -> User:
    try:
        user = db.scalar(select(User).where(User.username == data.username))
    except OperationalError:
        raise
    if user is None or not verify_password(data.password, user.hashed_password):
        raise InvalidCredentials
    if not user.is_active:
        raise AccountStopped
    return user


def get_current_user(db: Session, token: str) -> User:
    try:
        payload = decode_access_token(token)
        user_id = UUID(payload["sub"])
    except (TokenError, ValueError) as exc:
        raise NotAuthenticated from exc
    try:
        user = db.get(User, user_id)
    except OperationalError:
        raise
    if user is None or not user.is_active:
        raise NotAuthenticated
    return user


def authorize_user(user: User, *roles: UserRole) -> User:
    if user.role not in roles:
        raise NotAuthorized
    return user


def list_users(db: Session) -> list[User]:
    try:
        return list(db.scalars(select(User)))
    except OperationalError:
        raise


def set_user_access(db: Session, user_id: UUID, active: bool) -> User:
    try:
        user = db.get(User, user_id)
    except OperationalError:
        raise
    if user is None:
        raise UserNotFound
    user.is_active = active
    if not active:
        db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id)
            .values(revoked=True)
        )
    try:
        db.commit()
        db.refresh(user)
    except OperationalError:
        db.rollback()
        raise
    return user


def delete_user_account(db: Session, user_id: UUID) -> None:
    try:
        user = db.get(User, user_id)
    except OperationalError:
        raise
    if user is None:
        raise UserNotFound
    try:
        db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id)
            .values(replaced_by_id=None)
        )
        db.execute(delete(RefreshToken).where(RefreshToken.user_id == user_id))
        db.execute(delete(Subscription).where(Subscription.user_id == user_id))
        db.delete(user)
        db.commit()
    except OperationalError:
        db.rollback()
        raise
