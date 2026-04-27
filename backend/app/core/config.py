"""
Application configuration
Environment variables and settings management
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables

    Create a .env file in backend/ folder with these values:

    DATABASE_URL=postgresql+asyncpg://user:password@db/app_db
    SECRET_KEY=your-super-secret-key-change-in-production
    SESSION_SECRET_KEY=your-session-secret-change-in-production
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_ignore_empty=True, extra="ignore"
    )

    # Environment flag (defaults to development for local use)
    ENVIRONMENT: str = "development"

    # API Configuration
    PROJECT_NAME: str = "DevSecOps Social App API"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"

    # Database - Async PostgreSQL (Neon or local Docker)
    DATABASE_URL: str = "postgresql+asyncpg://user:password@db/app_db"

    # Security - JWT Tokens
    SECRET_KEY: str = "CHANGE-THIS-TO-A-SECURE-RANDOM-STRING-IN-PRODUCTION"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Security - Sessions (alternative to JWT for frontend preference)
    SESSION_SECRET_KEY: str = "CHANGE-THIS-SESSION-SECRET-IN-PRODUCTION"
    SESSION_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # CORS - Allow frontend to access API
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",      # React dev server
        "http://localhost:5173",      # Vite dev server
        "http://localhost:4173",      # Vite preview
    ]


# Create global settings instance
settings = Settings()
