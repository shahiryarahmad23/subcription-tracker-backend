from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin


class UsernameAlreadyExists(Exception):
    pass


class EmailAlreadyExists(Exception):
    pass


class InvalidCredentials(Exception):
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


def list_users(db: Session) -> list[User]:
    try:
        return list(db.scalars(select(User)))
    except OperationalError:
        raise
