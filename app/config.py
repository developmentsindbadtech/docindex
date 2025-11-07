"""Configuration management for the application."""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Azure AD Credentials
    azure_tenant_id: str
    azure_client_id: str
    azure_client_secret: str

    # Optional SharePoint Site IDs (comma-separated, empty = auto-discover)
    sharepoint_site_ids: Optional[str] = None

    # Cache Settings
    cache_ttl_seconds: int = 3600
    cache_max_size: int = 1000

    # Pagination Defaults
    default_page_size: int = 50
    max_page_size: int = 500

    # Logging
    log_level: str = "INFO"

    # Server Settings
    host: str = "0.0.0.0"
    port: int = Field(default=8000, description="Server port (use PORT env var for Cloud Run)")
    
    # Auto-detect port from environment (for Cloud Run)
    def __init__(self, **kwargs):
        import os
        if "PORT" in os.environ and "port" not in kwargs:
            kwargs["port"] = int(os.environ["PORT"])
        super().__init__(**kwargs)

    # SSO Authentication Settings
    sso_redirect_uri: Optional[str] = None  # Will be set based on deployment
    sso_allowed_domain: str = "sindbad.tech"  # Only allow @sindbad.tech emails
    session_secret_key: str = "change-this-to-a-random-secret-key-in-production"  # Change in production!

    class Config:
        """Pydantic config."""

        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()

