"""
Shared SQLAlchemy helpers used by the HigherMatch services.
"""

from contextlib import asynccontextmanager
import logging
from typing import Annotated, AsyncGenerator, TypeVar

from fastapi import Depends
from sqlalchemy import MetaData, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr
from sqlalchemy.pool import AsyncAdaptedQueuePool, NullPool
from sqlalchemy.sql import Select

from shared.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=convention)
T = TypeVar("T", bound=Mapped)


class Base(DeclarativeBase):
    metadata = metadata

    @declared_attr.directive
    def __tablename__(cls) -> str:
        import re

        return re.sub(r"(?<!^)(?=[A-Z])", "_", cls.__name__).lower()


def create_engine_with_config(settings: Settings) -> AsyncEngine:
    engine_kwargs: dict[str, object] = {
        "url": settings.database.async_url,
        "echo": settings.sql_echo,
        "pool_pre_ping": True,
    }

    if settings.is_production:
        engine_kwargs["poolclass"] = NullPool
    else:
        engine_kwargs["poolclass"] = AsyncAdaptedQueuePool
        engine_kwargs["pool_size"] = 10
        engine_kwargs["max_overflow"] = 20
        engine_kwargs["pool_recycle"] = 3600
        engine_kwargs["pool_timeout"] = 30

    logger.info(
        "Creating database engine for %s:%s/%s",
        settings.database.host,
        settings.database.port,
        settings.database.name,
    )
    return create_async_engine(**engine_kwargs)


def get_engine() -> AsyncEngine:
    return create_engine_with_config(get_settings())


engine = get_engine()


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )


async_session_factory = get_session_factory()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            await session.begin()
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


DBSession = Annotated[AsyncSession, Depends(get_db)]


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            await session.begin()
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    async with engine.begin() as conn:
        logger.info("Creating database tables")
        await conn.run_sync(Base.metadata.create_all)


async def drop_db() -> None:
    async with engine.begin() as conn:
        logger.warning("Dropping all database tables")
        await conn.run_sync(Base.metadata.drop_all)


async def check_db_health() -> bool:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.error("Database health check failed: %s", exc)
        return False


async def execute_select(
    db: AsyncSession,
    statement: Select,
    scalar: bool = False,
) -> list[T] | T | None:
    result = await db.execute(statement)
    if scalar:
        return result.scalar_one_or_none()
    return list(result.scalars().all())


async def execute_count(
    db: AsyncSession,
    statement: Select,
) -> int:
    result = await db.execute(statement)
    return result.scalar() or 0


async def dispose_engine() -> None:
    logger.info("Disposing database engine")
    await engine.dispose()


__all__ = [
    "Base",
    "engine",
    "async_session_factory",
    "metadata",
    "get_db",
    "DBSession",
    "get_db_context",
    "init_db",
    "drop_db",
    "check_db_health",
    "execute_select",
    "execute_count",
    "dispose_engine",
    "Select",
    "AsyncSession",
]
