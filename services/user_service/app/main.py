"""
User service application entrypoint.
"""

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncGenerator, Optional

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, hash_phone, init_jwt_manager
from app.database import User, dispose_db, get_db, init_db
from app.redis_client import close_redis, get_redis
from app.routers.auth import router as auth_router


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class Settings:
    SERVICE_NAME: str = os.getenv("SERVICE_NAME", "user-service")
    SERVICE_PORT: int = int(os.getenv("SERVICE_PORT", "8001"))
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://highermatch:highermatch@postgres:5432/highermatch_dev",
    )
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    CORS_ORIGINS: list[str] = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000",
    ).split(",")
    JWT_SECRET_KEY: str = os.getenv(
        "JWT_SECRET_KEY",
        "dev-secret-key-change-in-production",
    )
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    )
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = int(
        os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7")
    )


settings = Settings()


class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    full_name: Optional[str] = Field(default=None, max_length=200)
    phone: Optional[str] = Field(default=None, max_length=20)


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100)


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    name: Optional[str] = None
    company_name: Optional[str] = None
    company_size: Optional[str] = None
    is_candidate: Optional[bool] = None
    is_recruiter: Optional[bool] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    id: int
    name: Optional[str] = None
    company_name: Optional[str] = None
    company_size: Optional[str] = None
    role: Optional[str] = None
    is_active: bool
    is_verified: bool
    is_candidate: bool
    is_recruiter: bool
    created_at: datetime

    class Config:
        from_attributes = True


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    database: str


class MessageResponse(BaseModel):
    message: str
    success: bool = True


def _derive_role(is_candidate: bool, is_recruiter: bool) -> str:
    if is_recruiter:
        return "employer"
    if is_candidate:
        return "candidate"
    return "candidate"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Starting %s", settings.SERVICE_NAME)

    init_jwt_manager(
        secret_key=settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
        access_token_expire_minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
        refresh_token_expire_days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS,
    )
    await init_db()
    await get_redis()

    logger.info("%s started successfully", settings.SERVICE_NAME)
    yield

    logger.info("Shutting down %s", settings.SERVICE_NAME)
    await close_redis()
    await dispose_db()


app = FastAPI(
    title="HigherMatch User Service",
    description="HigherMatch user-service API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check(db: AsyncSession = Depends(get_db)):
    db_status = "unknown"
    try:
        await db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as exc:
        logger.error("Database health check failed: %s", exc)
        db_status = "unhealthy"

    return HealthResponse(
        status="healthy" if db_status == "healthy" else "degraded",
        service=settings.SERVICE_NAME,
        version="1.0.0",
        database=db_status,
    )


@app.get("/", tags=["Root"])
async def root():
    return {
        "service": "HigherMatch User Service",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
    }


@app.post(
    "/api/v1/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Users"],
)
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    existing_email = await db.execute(select(User.id).where(User.email == user.email))
    if existing_email.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    existing_username = await db.execute(select(User.id).where(User.username == user.username))
    if existing_username.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )

    new_user = User(
        email=user.email,
        username=user.username,
        hashed_password=hash_password(user.password),
        full_name=user.full_name,
        phone=user.phone,
        phone_hash=hash_phone(user.phone) if user.phone else None,
        role="candidate",
        name=user.full_name,
        is_candidate=True,
        is_recruiter=False,
        is_active=True,
        is_verified=False,
    )
    db.add(new_user)
    await db.flush()
    await db.refresh(new_user)

    logger.info("User created: %s - %s", new_user.id, new_user.username)
    return new_user


@app.get("/api/v1/users/{user_id}", response_model=UserResponse, tags=["Users"])
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


@app.get("/api/v1/users", response_model=list[UserResponse], tags=["Users"])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).order_by(User.created_at.desc()).offset(skip).limit(limit)
    )
    return list(result.scalars().all())


@app.patch("/api/v1/users/{user_id}", response_model=UserResponse, tags=["Users"])
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    update_data = user_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    if {"is_candidate", "is_recruiter"} & set(update_data.keys()):
        user.role = _derive_role(
            is_candidate=user.is_candidate,
            is_recruiter=user.is_recruiter,
        )

    if "full_name" in update_data and not user.name:
        user.name = user.full_name

    await db.flush()
    await db.refresh(user)

    logger.info("User updated: %s", user_id)
    return user


@app.delete(
    "/api/v1/users/{user_id}",
    response_model=MessageResponse,
    tags=["Users"],
)
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user.is_active = False
    await db.flush()

    logger.info("User soft-deleted: %s", user_id)
    return MessageResponse(message="User deleted successfully")


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.SERVICE_PORT,
        reload=os.getenv("RELOAD", "true").lower() == "true",
    )
