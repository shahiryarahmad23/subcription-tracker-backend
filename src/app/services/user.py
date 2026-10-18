from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.user import UserCreate


class UsernameAlreadyExists(Exception):
    pass


class EmailAlreadyExists(Exception):
    pass


def create_user(db: Session, data: UserCreate) -> User:
    user = User(**data.model_dump())
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
