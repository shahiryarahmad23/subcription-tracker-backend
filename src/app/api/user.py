from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.user import UserCreate, UserRead
from app.services.user import EmailAlreadyExists, UsernameAlreadyExists
from app.services.user import list_users as users_read
from app.services.user import register_user

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


@router.get("/", response_model=list[UserRead], status_code=status.HTTP_200_OK)
def read_users(db: Session = Depends(get_db)):
    try:
        users = users_read(db)
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
