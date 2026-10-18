import os
from typing import List, Optional
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Livguard Quotation Management System"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Environment ('development', 'test', 'production')
    ENVIRONMENT: str = "development"

    # Security: SECRET_KEY must be supplied via environment variable in production
    SECRET_KEY: Optional[str] = None
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 # 24 hours
    
    # Optional production initial bootstrap admin (never use default passwords in prod)
    INITIAL_ADMIN_EMAIL: Optional[str] = None
    INITIAL_ADMIN_PASSWORD: Optional[str] = None

    # Database
    DATABASE_URL: str = "sqlite:///./livguard.db"
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ]
    
    # Uploads & Storage
    UPLOAD_DIR: str = "./uploads"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow"
    )

    @model_validator(mode="after")
    def validate_security_settings(self) -> "Settings":
        env = (self.ENVIRONMENT or "development").strip().lower()
        secret = (self.SECRET_KEY or "").strip()

        # Known insecure placeholder fragments
        insecure_fragments = [
            "change-in-env",
            "change-me",
            "change-this",
            "super-secret-key",
            "default",
            "example",
            "placeholder",
            "secret123",
            "livguard-production-super-secret",
        ]

        if env == "production":
            if not secret:
                raise ValueError(
                    "CRITICAL SECURITY ERROR: SECRET_KEY must be explicitly set via environment configuration in production."
                )
            if len(secret) < 32:
                raise ValueError(
                    f"CRITICAL SECURITY ERROR: Production SECRET_KEY must be at least 32 characters long (provided: {len(secret)} characters)."
                )
            for frag in insecure_fragments:
                if frag in secret.lower():
                    raise ValueError(
                        f"CRITICAL SECURITY ERROR: Production SECRET_KEY cannot contain insecure placeholder pattern: '{frag}'."
                    )
            if self.DATABASE_URL.startswith("sqlite"):
                raise ValueError(
                    "CRITICAL SECURITY ERROR: SQLite cannot be used as a production database. Please configure a PostgreSQL connection string (e.g. Neon, RDS)."
                )
        else:
            # For development and test, provide a safe fallback if none was configured
            if not secret:
                self.SECRET_KEY = "livguard-dev-local-testing-secret-key-minimum-32-chars-long"

        return self

settings = Settings()

# Ensure upload directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
