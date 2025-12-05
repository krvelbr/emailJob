# app/config.py
import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App
    app_env: str = "development"
    app_debug: bool = True

    # Database
    database_url: str = "sqlite:///./emails.db"

    # Diretório de anexos (usado em main.py e no serviço)
    attachments_dir: str = os.path.join(os.path.dirname(__file__), "attachments")

    # Gmail / OAuth2 (IMAP)
    gmail_email: str
    gmail_imap_server: str = "imap.gmail.com"
    gmail_imap_port: int = 993

    gmail_client_id: str
    gmail_client_secret: str
    gmail_refresh_token: str

    gmail_oauth_scope: str = "https://mail.google.com/"
    gmail_token_uri: str = "https://oauth2.googleapis.com/token"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()