"""
Application configuration with Ollama settings.
"""
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


def clean_database_url(raw: Optional[str]) -> str:
    """
    Undo the usual copy-paste accidents with connection strings, which make
    SQLAlchemy fail at start-up with "Could not parse SQLAlchemy URL":
    - Neon's "psql" snippet:      psql 'postgresql://...'
    - quotes around the value:    "postgresql://..."  or  'postgresql://...'
    - the variable name included: DATABASE_URL=postgresql://...
    - spaces or a newline around it
    """
    url = (raw or "").strip()
    if url.upper().startswith("DATABASE_URL="):
        url = url[len("DATABASE_URL="):].strip()
    if url.lower().startswith("psql "):
        url = url[5:].strip()
    while len(url) >= 2 and url[0] == url[-1] and url[0] in "'\"":
        url = url[1:-1].strip()
    return url


class Settings:
    """Application settings."""

    # API
    API_TITLE = os.getenv("API_TITLE", "CodeAtlas API")
    API_VERSION = os.getenv("API_VERSION", "1.0.0")
    API_DESCRIPTION = os.getenv("API_DESCRIPTION", "AI-powered code intelligence platform")

    # Security
    API_KEY = os.getenv("API_KEY", "dev-key")
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    # Off unless DEBUG=true is set: debug mode exposes the AI proxy and admin routes.
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"

    # Server
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8000"))
    CLEANUP_ON_STARTUP = os.getenv("CLEANUP_ON_STARTUP", "true").lower() == "true"

    # LLM Configuration - Ollama
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-oss:120b-cloud")
    LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "60"))

    # Legacy OpenAI (kept for compatibility)
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4")

    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./codeatlas.db")

    # File storage
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", "storage/uploads")
    REPORT_DIR = os.getenv("REPORT_DIR", "storage/reports")
    EXPORT_DIR = os.getenv("EXPORT_DIR", "storage/exports")
    MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", 100 * 1024 * 1024))

    # Analysis
    MAX_WORKERS = int(os.getenv("MAX_WORKERS", 4))
    ANALYSIS_TIMEOUT = int(os.getenv("ANALYSIS_TIMEOUT", 300))

    # GitHub
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

    # CORS
    CORS_ORIGINS = [
        o.strip()
        for o in os.getenv(
            "CORS_ORIGINS", "http://localhost:3000,http://localhost:8000"
        ).split(",")
        if o.strip()
    ]

    # AI Features
    ENABLE_AI_SUMMARIES = os.getenv("ENABLE_AI_SUMMARIES", "true").lower() == "true"
    ENABLE_AI_README = os.getenv("ENABLE_AI_README", "true").lower() == "true"
    ENABLE_AI_INSIGHTS = os.getenv("ENABLE_AI_INSIGHTS", "true").lower() == "true"

    @property
    def database_url(self) -> str:
        """Get database URL with async support."""
        url = clean_database_url(self.DATABASE_URL)
        # One Postgres driver (psycopg 3) for both the async app and the sync
        # report store. It understands Neon's ?sslmode=require&channel_binding=require.
        for prefix in ("postgres://", "postgresql://", "postgresql+asyncpg://", "postgresql+psycopg2://"):
            if url.startswith(prefix):
                return "postgresql+psycopg://" + url[len(prefix):]
        if url.startswith("sqlite:///") and "aiosqlite" not in url:
            return url.replace("sqlite:///", "sqlite+aiosqlite:///")
        return url

    def ensure_directories(self) -> None:
        """Ensure required directories exist."""
        for directory in [self.UPLOAD_DIR, self.REPORT_DIR, self.EXPORT_DIR]:
            os.makedirs(directory, exist_ok=True)


# Global settings instance
settings = Settings()