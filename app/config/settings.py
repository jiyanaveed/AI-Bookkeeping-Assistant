from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App configuration; swap `DATABASE_URL` for Postgres when ready."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = ""
    receipt_vision_model: str = "gpt-4o-mini"
    companies_house_api_key: str = ""
    database_url: str = "sqlite:///./app.db"
    upload_dir: str = "./data/uploads"
    max_upload_mb: int = 15
    admin_api_key: str = ""

    @property
    def sqlalchemy_database_url(self) -> str:
        """Same as database_url; use a property if you later normalize SQLite paths."""
        return self.database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
