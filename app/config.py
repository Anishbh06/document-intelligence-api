from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    GEMINI_API_KEY: str
    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379/0"
    MAX_UPLOAD_SIZE_MB: int = 50
    RATE_LIMIT_REQUESTS: int = 60
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    LOG_LEVEL: str = "INFO"
    APP_ENV: str = "development"
    SECRET_KEY: str = "changeme"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()