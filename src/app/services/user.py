from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.core.security import TokenError, decode_access_token, hash_password, verify_password
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


def register_user(db: Session, data: UserCreate) -> User:
    payload = data.model_dump()
    payload["hashed_password"] = hash_password(payload.pop("password"))
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
    if user is None:
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
