"""
Application configuration with Ollama settings.
"""
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings."""
    
    # API
    API_TITLE = os.getenv("API_TITLE", "CodeAtlas API")
    API_VERSION = os.getenv("API_VERSION", "1.0.0")
    API_DESCRIPTION = os.getenv("API_DESCRIPTION", "AI-powered code intelligence platform")
    
    # Security
    API_KEY = os.getenv("API_KEY", "dev-key")
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    DEBUG = os.getenv("DEBUG", "True").lower() == "true"
    
    # LLM Configuration - UPDATED for Ollama
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")  # 'ollama' or 'openai'
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-oss:20b-cloud")  # or minimax-m2.5:cloud
    LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "60"))
    
    # Legacy OpenAI (kept for compatibility)
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4")
    
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./codeatlas.db")
    
    # File storage
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", "storage/uploads")
    REPORT_DIR = os.getenv("REPORT_DIR", "storage/reports")
    EXPORT_DIR = os.getenv("EXPORT_DIR", "storage/exports")
    MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", 100 * 1024 * 1024))  # 100MB
    
    # Analysis
    MAX_WORKERS = int(os.getenv("MAX_WORKERS", 4))
    ANALYSIS_TIMEOUT = int(os.getenv("ANALYSIS_TIMEOUT", 300))  # 5 minutes
    
    # GitHub
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    
    # CORS
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8000").split(",")
    
    # AI Features
    ENABLE_AI_SUMMARIES = os.getenv("ENABLE_AI_SUMMARIES", "true").lower() == "true"
    ENABLE_AI_README = os.getenv("ENABLE_AI_README", "true").lower() == "true"
    ENABLE_AI_INSIGHTS = os.getenv("ENABLE_AI_INSIGHTS", "true").lower() == "true"
    
    @property
    def database_url(self) -> str:
        """Get database URL with async support."""
        url = self.DATABASE_URL
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://")
        return url
    
    def ensure_directories(self) -> None:
        """Ensure required directories exist."""
        for directory in [self.UPLOAD_DIR, self.REPORT_DIR, self.EXPORT_DIR]:
            os.makedirs(directory, exist_ok=True)


# Global settings instance
settings = Settings()