"""
Shared configuration helpers used by the HigherMatch services.
"""

from functools import lru_cache
import os
from urllib.parse import quote_plus

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return int(value)


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return float(value)


def _env_csv(name: str, default: list[str]) -> list[str]:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return [item.strip() for item in value.split(",") if item.strip()]


class DatabaseSettings(BaseModel):
    host: str = Field(default_factory=lambda: os.getenv("POSTGRES_HOST", "localhost"))
    port: int = Field(default_factory=lambda: _env_int("POSTGRES_PORT", 5432))
    user: str = Field(default_factory=lambda: os.getenv("POSTGRES_USER", "highermatch"))
    password: str = Field(default_factory=lambda: os.getenv("POSTGRES_PASSWORD", ""))
    name: str = Field(default_factory=lambda: os.getenv("POSTGRES_DB", "highermatch_dev"))

    @property
    def async_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.user}:{quote_plus(self.password)}"
            f"@{self.host}:{self.port}/{self.name}"
        )

    @property
    def sync_url(self) -> str:
        return (
            f"postgresql://{self.user}:{quote_plus(self.password)}"
            f"@{self.host}:{self.port}/{self.name}"
        )


class RedisSettings(BaseModel):
    host: str = Field(default_factory=lambda: os.getenv("REDIS_HOST", "localhost"))
    port: int = Field(default_factory=lambda: _env_int("REDIS_PORT", 6379))
    password: str = Field(default_factory=lambda: os.getenv("REDIS_PASSWORD", ""))
    db: int = Field(default_factory=lambda: _env_int("REDIS_DB", 0))

    @property
    def url(self) -> str:
        if self.password:
            return f"redis://:{quote_plus(self.password)}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"

    @property
    def async_url(self) -> str:
        return self.url


class KafkaSettings(BaseModel):
    bootstrap_servers: str = Field(
        default_factory=lambda: os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    )
    consumer_group: str = Field(
        default_factory=lambda: os.getenv("KAFKA_CONSUMER_GROUP", "highermatch-consumers")
    )
    auto_offset_reset: str = Field(default="earliest")
    enable_auto_commit: bool = Field(default=True)
    security_protocol: str = Field(default="PLAINTEXT")
    sasl_mechanism: str = Field(default="PLAIN")
    sasl_plain_username: str = Field(default_factory=lambda: os.getenv("KAFKA_SASL_USERNAME", ""))
    sasl_plain_password: str = Field(default_factory=lambda: os.getenv("KAFKA_SASL_PASSWORD", ""))


class QdrantSettings(BaseModel):
    host: str = Field(default_factory=lambda: os.getenv("QDRANT_HOST", "localhost"))
    port: int = Field(default_factory=lambda: _env_int("QDRANT_PORT", 6333))
    grpc_port: int = Field(default_factory=lambda: _env_int("QDRANT_GRPC_PORT", 6334))
    collection_name: str = Field(
        default_factory=lambda: os.getenv("QDRANT_COLLECTION_NAME", "job_candidates")
    )
    vector_size: int = Field(default_factory=lambda: _env_int("EMBEDDING_DIMENSIONS", 1536))
    distance: str = Field(default="Cosine")

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"


class JWTSettings(BaseModel):
    secret_key: str = Field(
        default_factory=lambda: os.getenv(
            "JWT_SECRET_KEY", "dev-secret-key-change-in-production"
        )
    )
    algorithm: str = Field(default_factory=lambda: os.getenv("JWT_ALGORITHM", "HS256"))
    access_token_expire_minutes: int = Field(
        default_factory=lambda: _env_int("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", 30)
    )
    refresh_token_expire_days: int = Field(
        default_factory=lambda: _env_int("JWT_REFRESH_TOKEN_EXPIRE_DAYS", 7)
    )


class CORSSettings(BaseModel):
    allow_origins: list[str] = Field(
        default_factory=lambda: _env_csv(
            "CORS_ORIGINS", ["http://localhost:3000", "http://localhost:8080"]
        )
    )
    allow_methods: list[str] = Field(default_factory=lambda: ["*"])
    allow_headers: list[str] = Field(default_factory=lambda: ["*"])
    allow_credentials: bool = Field(default=True)


class LogSettings(BaseModel):
    level: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    format: str = Field(default_factory=lambda: os.getenv("LOG_FORMAT", "json"))
    file_path: str = Field(default="/app/logs/app.log")
    max_bytes: int = Field(
        default_factory=lambda: _env_int("LOG_FILE_MAX_SIZE_MB", 100) * 1024 * 1024
    )
    backup_count: int = Field(default_factory=lambda: _env_int("LOG_FILE_BACKUP_COUNT", 5))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    service_name: str = Field(default_factory=lambda: os.getenv("SERVICE_NAME", "highermatch-service"))
    environment: str = Field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    debug: bool = Field(default_factory=lambda: _env_bool("DEBUG", True))
    api_port: int = Field(default_factory=lambda: _env_int("SERVICE_PORT", 8000))

    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    kafka: KafkaSettings = Field(default_factory=KafkaSettings)
    qdrant: QdrantSettings = Field(default_factory=QdrantSettings)
    jwt: JWTSettings = Field(default_factory=JWTSettings)
    cors: CORSSettings = Field(default_factory=CORSSettings)
    log: LogSettings = Field(default_factory=LogSettings)

    match_score_threshold: float = Field(
        default_factory=lambda: _env_float("MATCH_SCORE_THRESHOLD", 0.75)
    )
    max_recommendations: int = Field(
        default_factory=lambda: _env_int("MAX_JOB_RECOMMENDATIONS", 20)
    )
    ai_temperature: float = Field(default_factory=lambda: _env_float("AI_TEMPERATURE", 0.7))

    openai_api_key: str = Field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY", os.getenv("LLM_API_KEY", ""))
    )
    openai_model: str = Field(
        default_factory=lambda: os.getenv("OPENAI_MODEL", os.getenv("LLM_MODEL", "qwen3.5-plus"))
    )
    openai_base_url: str = Field(
        default_factory=lambda: os.getenv(
            "OPENAI_BASE_URL",
            os.getenv("LLM_API_BASE", os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")),
        )
    )
    openai_max_tokens: int = Field(default_factory=lambda: _env_int("OPENAI_MAX_TOKENS", 2000))

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, value: str) -> str:
        allowed = {"development", "staging", "production"}
        if value not in allowed:
            raise ValueError(f"environment must be one of {allowed}")
        return value

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def sql_echo(self) -> bool:
        return _env_bool("SQL_ECHO", self.debug and self.is_development)

    # Compatibility helpers for services that use uppercase settings names.
    @property
    def SERVICE_NAME(self) -> str:
        return self.service_name

    @property
    def SERVICE_PORT(self) -> int:
        return self.api_port

    @property
    def DATABASE_URL(self) -> str:
        return self.database.async_url

    @property
    def REDIS_URL(self) -> str:
        return self.redis.url

    @property
    def KAFKA_BOOTSTRAP_SERVERS(self) -> str:
        return self.kafka.bootstrap_servers

    @property
    def QDRANT_URL(self) -> str:
        return self.qdrant.url

    @property
    def JWT_SECRET_KEY(self) -> str:
        return self.jwt.secret_key

    @property
    def CORS_ORIGINS(self) -> list[str]:
        return self.cors.allow_origins

    @property
    def LOG_LEVEL(self) -> str:
        return self.log.level

    @property
    def LOG_FORMAT(self) -> str:
        return self.log.format

    @property
    def OPENAI_API_KEY(self) -> str:
        return self.openai_api_key

    @property
    def OPENAI_MODEL(self) -> str:
        return self.openai_model

    @property
    def OPENAI_BASE_URL(self) -> str:
        return self.openai_base_url

    @property
    def OPENAI_MAX_TOKENS(self) -> int:
        return self.openai_max_tokens

    @property
    def MATCH_SCORE_THRESHOLD(self) -> float:
        return self.match_score_threshold


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
