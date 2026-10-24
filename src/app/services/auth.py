import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import generate_refresh_token, hash_refresh_token
from app.models.refresh_token import RefreshToken


class RefreshTokenReuse(Exception):
    pass


class InvalidRefreshToken(Exception):
    pass


def start_refresh_session(db: Session, user_id: uuid.UUID) -> str:
    raw_token = generate_refresh_token()
    db.add(
        RefreshToken(
            user_id=user_id,
            token_hash=hash_refresh_token(raw_token),
            family_id=uuid.uuid4(),
            expires_at=_expires_at(),
        )
    )
    db.commit()
    return raw_token


def rotate_refresh_session(db: Session, raw_token: str) -> tuple[str, uuid.UUID]:
    current = db.scalar(
        select(RefreshToken)
        .where(RefreshToken.token_hash == hash_refresh_token(raw_token))
        .with_for_update()
    )
    if current is None:
        raise InvalidRefreshToken("Invalid refresh token")

    now = datetime.now(timezone.utc)
    if current.revoked:
        db.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == current.family_id)
            .values(revoked=True)
        )
        db.commit()
        raise RefreshTokenReuse("Refresh token reuse detected")
    if current.expires_at <= now:
        db.rollback()
        raise InvalidRefreshToken("Refresh token expired")

    raw_replacement = generate_refresh_token()
    replacement = RefreshToken(
        user_id=current.user_id,
        token_hash=hash_refresh_token(raw_replacement),
        family_id=current.family_id,
        expires_at=_expires_at(now),
    )
    db.add(replacement)
    db.flush()
    current.revoked = True
    current.replaced_by_id = replacement.id
    db.commit()
    return raw_replacement, current.user_id


def end_refresh_session(db: Session, raw_token: str, user_id: uuid.UUID) -> None:
    current = db.scalar(
        select(RefreshToken)
        .where(RefreshToken.token_hash == hash_refresh_token(raw_token))
        .with_for_update()
    )
    if current is None or current.user_id != user_id:
        raise InvalidRefreshToken("Invalid refresh token")
    current.revoked = True
    db.commit()


def _expires_at(now: datetime | None = None) -> datetime:
    current = now or datetime.now(timezone.utc)
    return current + timedelta(minutes=settings.refresh_token_expire_minutes)
