from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./golf_deals.db"
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-5"
    admin_api_token: str = "change-me-to-a-random-secret"
    cors_origins: str = "http://localhost:3000"
    rakuten_app_id: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
