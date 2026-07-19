from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Pegasus AI"
    DATABASE_URL: str
    REDIS_URL: str
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()