from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Aereo Geospatial File Measurement API"
    APP_NAME: str = "aereo-geospatial-api"
    API_V1_STR: str = "/api"
    MAX_UPLOAD_SIZE_BYTES: int = 20 * 1024 * 1024
    MAX_ZIP_MEMBER_SIZE_BYTES: int = 10 * 1024 * 1024
    MAX_ZIP_TOTAL_SIZE_BYTES: int = 100 * 1024 * 1024
    MAX_ZIP_ENTRIES: int = 500
    MAX_ZIP_COMPRESSION_RATIO: float = 100.0
    DATABASE_URL: str = "sqlite:///./aereo.db"
    DB_ECHO: bool = False
    ENVIRONMENT: str = "local"
    POSTGRES_DB: str = "aereo"
    POSTGRES_USER: str = "aereo"
    POSTGRES_PASSWORD: str = "aereo"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
