"""
Authentication business logic for the user service.
"""

import hashlib
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    create_refresh_token,
    encrypt_phone,
    hash_password,
    hash_phone,
    login_rate_limiter,
    verify_password,
    verify_refresh_token,
)
from app.database import User as DbUser
from app.schemas.auth import (
    ErrorDetail,
    ErrorResponse,
    LoginRequest,
    LoginResponse,
    RefreshTokenResponse,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserInfo,
    UserMeResponse,
    UserRole,
)


logger = logging.getLogger(__name__)

MSG_DUPLICATE_USERNAME = "\u7528\u6237\u540d\u5df2\u88ab\u5360\u7528"
MSG_DUPLICATE_EMAIL = "\u8be5\u90ae\u7bb1\u5df2\u88ab\u6ce8\u518c"
MSG_DUPLICATE_PHONE = "\u8be5\u624b\u673a\u53f7\u5df2\u88ab\u6ce8\u518c"
MSG_DUPLICATE_EMAIL_OR_PHONE = "\u90ae\u7bb1\u6216\u624b\u673a\u53f7\u5df2\u88ab\u6ce8\u518c"
MSG_ACCOUNT_DISABLED = "\u8d26\u53f7\u5df2\u88ab\u7981\u7528"
MSG_INVALID_CREDENTIALS = "\u90ae\u7bb1\u6216\u5bc6\u7801\u9519\u8bef"
MSG_INVALID_TOKEN = "Token \u65e0\u6548\u6216\u5df2\u8fc7\u671f"
MSG_ACCOUNT_LOCKED = "\u767b\u5f55\u5931\u8d25\u6b21\u6570\u8fc7\u591a\uff0c\u8d26\u53f7\u5df2\u88ab\u9501\u5b9a"
MSG_PERMISSION_DENIED = "\u6743\u9650\u4e0d\u8db3"


class User:
    """In-memory auth user model."""

    def __init__(
        self,
        id: str,
        email: str,
        phone_hash: str,
        hashed_password: str,
        role: str,
        phone: Optional[str] = None,
        name: Optional[str] = None,
        company_name: Optional[str] = None,
        company_size: Optional[str] = None,
        is_verified: bool = False,
        is_active: bool = True,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        self.id = id
        self.email = email
        self.phone_hash = phone_hash
        self.phone = phone
        self.hashed_password = hashed_password
        self.role = role
        self.name = name
        self.company_name = company_name
        self.company_size = company_size
        self.is_verified = is_verified
        self.is_active = is_active
        self.created_at = created_at or datetime.now(timezone.utc)
        self.updated_at = updated_at or datetime.now(timezone.utc)

    def to_user_info(self) -> UserInfo:
        encrypted_phone = encrypt_phone(self.phone) if self.phone else None
        return UserInfo(
            id=self.id,
            email=self.email,
            phone=encrypted_phone,
            role=UserRole(self.role),
            name=self.name or self.company_name,
            is_verified=self.is_verified,
            created_at=self.created_at,
        )

    @classmethod
    def from_db_row(cls, row: DbUser) -> "User":
        return cls(
            id=str(row.id),
            email=row.email,
            phone_hash=row.phone_hash or "",
            phone=row.phone,
            hashed_password=row.hashed_password,
            role=row.role or _derive_role(row.is_candidate, row.is_recruiter),
            name=row.name or row.full_name,
            company_name=row.company_name,
            company_size=row.company_size,
            is_verified=row.is_verified,
            is_active=row.is_active,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


def _derive_role(is_candidate: bool, is_recruiter: bool) -> str:
    if is_recruiter:
        return UserRole.EMPLOYER.value
    if is_candidate:
        return UserRole.CANDIDATE.value
    return UserRole.CANDIDATE.value


class UserRepository:
    """Persistence layer used by the auth service."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def _uses_mock_repository(self) -> bool:
        return not hasattr(self.db, "execute")

    async def get_by_email(self, email: str) -> Optional[User]:
        if self._uses_mock_repository():
            return await self.db.get_by_email(email)

        result = await self.db.execute(select(DbUser).where(DbUser.email == email))
        db_user = result.scalar_one_or_none()
        return User.from_db_row(db_user) if db_user else None

    async def get_by_id(self, user_id: str) -> Optional[User]:
        if self._uses_mock_repository():
            return await self.db.get_by_id(user_id)

        try:
            normalized_id = int(user_id)
        except (TypeError, ValueError):
            return None

        result = await self.db.execute(select(DbUser).where(DbUser.id == normalized_id))
        db_user = result.scalar_one_or_none()
        return User.from_db_row(db_user) if db_user else None

    async def get_by_phone_hash(self, phone_hash_value: str) -> Optional[User]:
        if self._uses_mock_repository():
            return await self.db.get_by_phone_hash(phone_hash_value)

        result = await self.db.execute(
            select(DbUser).where(DbUser.phone_hash == phone_hash_value)
        )
        db_user = result.scalar_one_or_none()
        return User.from_db_row(db_user) if db_user else None

    async def create(self, user_data: dict) -> User:
        if self._uses_mock_repository():
            mock_payload = {
                key: value
                for key, value in user_data.items()
                if key
                in {
                    "email",
                    "phone_hash",
                    "hashed_password",
                    "role",
                    "name",
                    "company_name",
                    "company_size",
                }
            }
            return await self.db.create(mock_payload)

        role = user_data["role"]
        username = await self._generate_unique_username(user_data["email"])
        full_name = user_data.get("name") or user_data.get("company_name")

        db_user = DbUser(
            email=user_data["email"],
            username=username,
            hashed_password=user_data["hashed_password"],
            full_name=full_name,
            phone=user_data.get("phone"),
            phone_hash=user_data.get("phone_hash"),
            role=role,
            name=user_data.get("name"),
            company_name=user_data.get("company_name"),
            company_size=user_data.get("company_size"),
            is_active=True,
            is_verified=False,
            is_candidate=role == UserRole.CANDIDATE.value,
            is_recruiter=role == UserRole.EMPLOYER.value,
        )

        self.db.add(db_user)
        await self.db.flush()
        await self.db.refresh(db_user)

        logger.info("User created: %s, role=%s", db_user.id, role)
        return User.from_db_row(db_user)

    async def _generate_unique_username(self, email: str) -> str:
        local_part = email.split("@", 1)[0].lower()
        normalized = re.sub(r"[^a-z0-9]+", "_", local_part).strip("_") or "user"
        candidate = normalized[:80]

        for attempt in range(10):
            username = candidate if attempt == 0 else f"{candidate}_{attempt}"
            result = await self.db.execute(select(DbUser.id).where(DbUser.username == username))
            if result.scalar_one_or_none() is None:
                return username

        suffix = hashlib.sha256(email.encode("utf-8")).hexdigest()[:8]
        username = f"{candidate[:70]}_{suffix}"
        result = await self.db.execute(select(DbUser.id).where(DbUser.username == username))
        if result.scalar_one_or_none() is None:
            return username

        raise DuplicateError(field="username", message=MSG_DUPLICATE_USERNAME)


class AuthService:
    """Authentication service."""

    def __init__(self, db: AsyncSession, redis_client) -> None:
        self.db = db
        self.redis = redis_client
        self.user_repo = UserRepository(db)

    async def register(self, request: RegisterRequest) -> RegisterResponse:
        existing_user = await self.user_repo.get_by_email(request.email)
        if existing_user:
            raise DuplicateError(field="email", message=MSG_DUPLICATE_EMAIL)

        phone_hash_value = hash_phone(request.phone)
        existing_phone = await self.user_repo.get_by_phone_hash(phone_hash_value)
        if existing_phone:
            raise DuplicateError(field="phone", message=MSG_DUPLICATE_PHONE)

        user_data = {
            "email": request.email,
            "phone": request.phone,
            "phone_hash": phone_hash_value,
            "hashed_password": hash_password(request.password),
            "role": request.role.value,
            "name": request.name,
            "company_name": request.company_name,
            "company_size": request.company_size,
        }

        try:
            user = await self.user_repo.create(user_data)
        except IntegrityError as exc:
            logger.warning("Registration integrity error: %s", exc)
            raise DuplicateError(
                field="email",
                message=MSG_DUPLICATE_EMAIL_OR_PHONE,
            ) from exc

        token_response = self._create_tokens(user)
        logger.info("User registered: %s, role=%s", user.id, user.role)

        return RegisterResponse(
            user_id=user.id,
            role=UserRole(user.role),
            token=token_response,
        )

    async def login(self, request: LoginRequest) -> LoginResponse:
        identifier = request.email

        if self.redis is not None and await login_rate_limiter.is_locked(identifier, self.redis):
            remaining = await login_rate_limiter.get_lockout_remaining_seconds(
                identifier,
                self.redis,
            )
            locked_until = datetime.now(timezone.utc) + timedelta(seconds=remaining)
            raise AccountLockedError(retry_after=remaining, locked_until=locked_until)

        user = await self.user_repo.get_by_email(request.email)
        if not user:
            remaining = None
            if self.redis is not None:
                await login_rate_limiter.record_failure(identifier, self.redis)
                remaining = await login_rate_limiter.get_remaining_attempts(
                    identifier,
                    self.redis,
                )
            raise InvalidCredentialsError(remaining_attempts=remaining)

        if not verify_password(request.password, user.hashed_password):
            if self.redis is not None:
                attempts = await login_rate_limiter.record_failure(identifier, self.redis)
                if attempts >= 5:
                    remaining = await login_rate_limiter.get_lockout_remaining_seconds(
                        identifier,
                        self.redis,
                    )
                    locked_until = datetime.now(timezone.utc) + timedelta(seconds=remaining)
                    raise AccountLockedError(
                        retry_after=remaining,
                        locked_until=locked_until,
                    )

                remaining = await login_rate_limiter.get_remaining_attempts(
                    identifier,
                    self.redis,
                )
                raise InvalidCredentialsError(remaining_attempts=remaining)

            raise InvalidCredentialsError()

        if not user.is_active:
            raise InvalidCredentialsError(message=MSG_ACCOUNT_DISABLED)

        if self.redis is not None:
            await login_rate_limiter.record_success(identifier, self.redis)

        token_response = self._create_tokens(user)
        logger.info("User logged in: %s", user.id)

        return LoginResponse(
            access_token=token_response.access_token,
            refresh_token=token_response.refresh_token,
            token_type=token_response.token_type,
            user_id=user.id,
            role=UserRole(user.role),
        )

    async def refresh_token(self, refresh_token: str) -> RefreshTokenResponse:
        payload = verify_refresh_token(refresh_token)
        user_id = payload.get("sub")

        if not user_id:
            raise InvalidTokenError("Invalid token")

        user = await self.user_repo.get_by_id(str(user_id))
        if not user:
            raise InvalidTokenError("User not found")

        if not user.is_active:
            raise InvalidCredentialsError(message=MSG_ACCOUNT_DISABLED)

        token_response = self._create_tokens(user)
        logger.info("Token refreshed for user: %s", user_id)

        return RefreshTokenResponse(
            access_token=token_response.access_token,
            refresh_token=token_response.refresh_token,
            token_type=token_response.token_type,
            expires_in=token_response.expires_in,
        )

    async def get_current_user(self, user_id: str) -> UserMeResponse:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise InvalidTokenError("User not found")

        return UserMeResponse(success=True, data=user.to_user_info())

    def _create_tokens(self, user: User) -> TokenResponse:
        access_token = create_access_token(
            subject=user.id,
            role=user.role,
            additional_claims={"email": user.email},
        )
        refresh_token = create_refresh_token(subject=user.id)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )


class AuthError(Exception):
    """Base auth exception."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: Optional[dict] = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)

    def to_error_response(self) -> ErrorResponse:
        return ErrorResponse(
            success=False,
            error=ErrorDetail(
                code=self.code,
                message=self.message,
                details=self.details,
            ),
        )


class DuplicateError(AuthError):
    """Duplicate record exception."""

    def __init__(self, field: str, message: str) -> None:
        super().__init__(
            code="AUTH_3002",
            message=message,
            status_code=409,
            details={"field": field},
        )


class InvalidCredentialsError(AuthError):
    """Invalid credentials exception."""

    def __init__(
        self,
        message: str = MSG_INVALID_CREDENTIALS,
        remaining_attempts: Optional[int] = None,
    ) -> None:
        details = {}
        if remaining_attempts is not None:
            details["remaining_attempts"] = remaining_attempts

        super().__init__(
            code="AUTH_2001",
            message=message,
            status_code=401,
            details=details or None,
        )


class InvalidTokenError(AuthError):
    """Invalid token exception."""

    def __init__(self, message: str = MSG_INVALID_TOKEN) -> None:
        super().__init__(
            code="AUTH_2001",
            message=message,
            status_code=401,
        )


class AccountLockedError(AuthError):
    """Account locked exception."""

    def __init__(self, retry_after: int, locked_until: datetime) -> None:
        super().__init__(
            code="AUTH_2004",
            message=MSG_ACCOUNT_LOCKED,
            status_code=429,
            details={
                "retry_after": retry_after,
                "locked_until": locked_until.isoformat(),
            },
        )
        self.retry_after = retry_after
        self.locked_until = locked_until


class InsufficientPermissionError(AuthError):
    """Permission exception."""

    def __init__(self, message: str = MSG_PERMISSION_DENIED) -> None:
        super().__init__(
            code="AUTH_2003",
            message=message,
            status_code=403,
        )


__all__ = [
    "User",
    "UserRepository",
    "AuthService",
    "AuthError",
    "DuplicateError",
    "InvalidCredentialsError",
    "InvalidTokenError",
    "AccountLockedError",
    "InsufficientPermissionError",
]
