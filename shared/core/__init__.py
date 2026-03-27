"""
HigherMatch shared core package.

Only export the configuration and database primitives that are required by
the running services. Heavier helpers stay available via direct submodule
imports, which avoids import-time side effects during service startup.
"""

from shared.core.config import (
    CORSSettings,
    DatabaseSettings,
    JWTSettings,
    KafkaSettings,
    LogSettings,
    QdrantSettings,
    RedisSettings,
    Settings,
    get_settings,
    settings,
)
from shared.core.db import (
    AsyncSession,
    Base,
    DBSession,
    Select,
    async_session_factory,
    check_db_health,
    dispose_engine,
    drop_db,
    engine,
    execute_count,
    execute_select,
    get_db,
    get_db_context,
    init_db,
    metadata,
)

__version__ = "1.0.0"

__all__ = [
    "Settings",
    "DatabaseSettings",
    "RedisSettings",
    "KafkaSettings",
    "QdrantSettings",
    "JWTSettings",
    "CORSSettings",
    "LogSettings",
    "get_settings",
    "settings",
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
    "AsyncSession",
    "Select",
]
