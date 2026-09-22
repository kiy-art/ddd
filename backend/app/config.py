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
    rakuten_access_key: str = ""
    rakuten_referer: str = "https://golf-deals-backend.onrender.com"
    rakuten_affiliate_id: str = ""
    yahoo_client_id: str = ""
    yahoo_affiliate_id: str = ""
    resend_api_key: str = ""
    # Resend's own shared sending address - works with zero setup (no
    # domain verification, no cost) on the free plan, which is exactly why
    # it's the default here. A verified custom domain (optional, still
    # free) can be swapped in later by just changing this env var.
    resend_from_email: str = "PAR. <onboarding@resend.dev>"
    # The public frontend URL, used to build a clickable product link inside
    # price-alert emails. Defaults to the real production URL (confirmed
    # working during the Yahoo! Developer Network registration) rather than
    # localhost, since email links need to work outside this dev sandbox.
    site_url: str = "https://golf-deals-frontend.onrender.com"
    ga4_property_id: str = ""
    ga4_service_account_json: str = ""
    # X (Twitter) API v2 - OAuth 1.0a user-context credentials for the site's
    # own posting account (see app/x_post.py). All four are required together;
    # posting is skipped entirely (not an error) when any is unset, matching
    # how yahoo_client_id/resend_api_key are treated as optional integrations.
    x_api_key: str = ""
    x_api_secret: str = ""
    x_access_token: str = ""
    x_access_token_secret: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
