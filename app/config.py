from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # OpenAI
    OPENAI_API_KEY: str

    # Database
    DATABASE_URL: str

    # App
    APP_ENV: str = "development"
    SECRET_KEY: str = "changeme"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()