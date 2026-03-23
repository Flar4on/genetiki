from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Telegram
    bot_token: str

    # Database
    database_url: str = "postgresql+asyncpg://rns:rns_password@db:5432/rns_db"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # Security
    secret_key: str = "change-me"
    encryption_key: str = "change-me"
    access_token_expire_minutes: int = 60 * 24  # 24 hours

    # API
    api_key: str = "change-me"

    # Admin defaults
    admin_email: str = "admin@rns.local"
    admin_password: str = "change-me"

    # Notification settings
    notification_retry_interval_hours: int = 2
    notification_max_retries: int = 3
    notification_escalation_hours: int = 24

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
