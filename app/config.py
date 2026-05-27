from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "项目运行管理系统"
    app_env: str = "dev"
    secret_key: str = "dev-secret-change-me"
    access_token_expire_minutes: int = 480
    database_url: str = "postgresql+psycopg://project_support:project_support@127.0.0.1:5432/project_support"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
