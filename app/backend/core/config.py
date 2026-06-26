from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://print_manager:change-me@localhost:5432/print_manager"
    backend_cors_origins: str = "http://localhost:8501"
    ai_openai_enabled: bool = False
    openai_api_key: str | None = None
    openai_product_model: str = "gpt-5.4-mini"
    openai_api_base_url: str = "https://api.openai.com/v1"
    ai_product_max_output_tokens: int = 2500

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
