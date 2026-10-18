from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class UserCreate(BaseModel):
    username: str
    hashed_password: str
    email: str
    dob: date


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
