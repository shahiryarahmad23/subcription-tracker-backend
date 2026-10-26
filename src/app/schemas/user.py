from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.user import UserRole


class UserCreate(BaseModel):
    username: str = Field(
        description="Unique login name. Used later with password at POST /user/login.",
        examples=["ada"],
    )
    password: str = Field(
        description="Plain-text password. The server stores only an Argon2 hash. It is never returned.",
    )
    email: str = Field(
        description="Unique email address for this account.",
        examples=["ada@example.com"],
    )
    dob: date = Field(
        description="Date of birth as YYYY-MM-DD. This is a calendar date, not a time.",
        examples=["1990-04-01"],
    )
    role: UserRole | None = Field(
        default=None,
        description="Omit this field, or send user, to create a normal account. Send admin to create an admin.",
    )


class UserLogin(BaseModel):
    username: str = Field(description="The username sent at registration.")
    password: str = Field(description="The same plain-text password sent at registration.")


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(description="UUID of the user account.")
    username: str = Field(description="Login name.")
    email: str = Field(description="Email address.")
    role: UserRole = Field(description="user or admin.")
    is_active: bool = Field(description="False when an admin has stopped this account from signing in.")


class TokenPair(BaseModel):
    access_token: str = Field(
        description="JWT access token. Send as Authorization: Bearer <access_token>. Expires in 15 minutes."
    )
    refresh_token: str = Field(
        description="Opaque refresh token. Send it only to POST /user/logout. It is not a JWT."
    )
    token_type: str = Field(default="bearer", description="Always bearer.")


class LogoutRequest(BaseModel):
    refresh_token: str = Field(
        description="The opaque refresh token returned by POST /user/login. This revokes that login session."
    )


class UserAccessUpdate(BaseModel):
    active: bool = Field(description="False stops the account from signing in. True restores it.")
