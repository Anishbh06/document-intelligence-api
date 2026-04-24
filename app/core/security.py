from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import APIError
from app.db.session import get_db

# ── password hashing ──────────────────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ── JWT helpers ───────────────────────────────────────────────────────────────
bearer_scheme = HTTPBearer(auto_error=False)


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def _decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise APIError(status_code=401, code="invalid_token", message="Invalid or expired token")


# ── FastAPI dependency ────────────────────────────────────────────────────────
async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
):
    """Validate Bearer JWT and return the active User row."""
    from app.models.user import User  # local import to avoid circular
    from app.repositories.user_repo import UserRepository

    if not credentials:
        raise APIError(status_code=401, code="unauthorized", message="Authentication required")

    payload = _decode_token(credentials.credentials)
    username: str | None = payload.get("sub")
    if not username:
        raise APIError(status_code=401, code="invalid_token", message="Invalid token payload")

    repo = UserRepository(db)
    user = await repo.get_by_username(username)
    if not user or not user.is_active:
        raise APIError(status_code=401, code="unauthorized", message="User not found or inactive")

    return user
