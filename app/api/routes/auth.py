from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import APIError
from app.core.security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.db.session import get_db
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.schemas.user import TokenResponse, UserCreate, UserLogin, UserResponse

router = APIRouter()


@router.post("/auth/register", response_model=TokenResponse, status_code=201)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    """Create a new account and return an access token immediately."""
    repo = UserRepository(db)

    if await repo.get_by_username(payload.username):
        raise APIError(status_code=409, code="username_taken", message="Username already exists")
    if await repo.get_by_email(payload.email):
        raise APIError(status_code=409, code="email_taken", message="Email already registered")

    user = await repo.create_user(
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )

    token = create_access_token({"sub": user.username})
    return TokenResponse(access_token=token, user=UserResponse.model_validate(user))


@router.post("/auth/login", response_model=TokenResponse)
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)):
    """Authenticate and return a JWT access token."""
    repo = UserRepository(db)
    user = await repo.get_by_username(payload.username)

    if not user or not verify_password(payload.password, user.hashed_password):
        raise APIError(
            status_code=401,
            code="invalid_credentials",
            message="Invalid username or password",
        )
    if not user.is_active:
        raise APIError(status_code=403, code="account_disabled", message="Account is disabled")

    token = create_access_token({"sub": user.username})
    return TokenResponse(access_token=token, user=UserResponse.model_validate(user))


@router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return UserResponse.model_validate(current_user)
