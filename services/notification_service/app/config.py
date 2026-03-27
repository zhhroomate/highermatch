"""
Configuration Settings
Notification Service
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings"""

    # Service
    SERVICE_NAME: str = "notification-service"
    LOG_LEVEL: str = "INFO"

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_CONSUMER_GROUP: str = "notification-service"
    KAFKA_AUTO_OFFSET_RESET: str = "earliest"

    # Kafka Topics to consume
    KAFKA_TOPIC_MATCH_COMPLETED: str = "match.completed"
    KAFKA_TOPIC_INVOICE_GENERATED: str = "invoice.generated"
    KAFKA_TOPIC_GUARANTEE_CREATED: str = "guarantee.created"
    KAFKA_TOPIC_CLAIM_APPROVED: str = "claim.approved"
    KAFKA_TOPIC_CLAIM_REJECTED: str = "claim.rejected"

    # SMTP Settings
    SMTP_HOST: str = "smtp.example.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = "notifications@highermatch.com"
    SMTP_PASSWORD: str = ""
    SMTP_FROM_NAME: str = "HigherMatch"
    SMTP_FROM_EMAIL: str = "notifications@highermatch.com"
    SMTP_USE_TLS: bool = True

    # Email Config
    EMAIL_ENABLED: bool = True
    EMAIL_DEV_MODE: bool = False  # If True, print emails to console instead of sending
    EMAIL_DEV_RECIPIENT: str = "dev@highermatch.com"

    # Retry Settings
    EMAIL_MAX_RETRIES: int = 3
    EMAIL_RETRY_DELAY: int = 5  # seconds

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings"""
    return Settings()
