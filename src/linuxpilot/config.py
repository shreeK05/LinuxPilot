"""
Configuration management for LinuxPilot
"""

from pydantic_settings import BaseSettings
from typing import Optional
from pathlib import Path


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    PROJECT_NAME: str = "LinuxPilot"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # API
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8000
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = "sqlite:///./linuxpilot.db"
    
    # LLM Providers
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:7b-instruct"
    
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-flash"
    
    # Fallback chain order
    LLM_PROVIDER_ORDER: list[str] = ["ollama", "groq", "gemini"]
    
    # Cassette (recording/replay) mode
    CASSETTE_MODE: bool = False
    CASSETTE_DIR: Path = Path("./cassettes")
    
    # Sandbox
    SANDBOX_ENABLED: bool = True
    SANDBOX_HELPER_PROFILE: str = "helper-strict"
    SANDBOX_APP_PROFILE: str = "app-gui"
    
    # Resource limits
    DEFAULT_MEMORY_LIMIT_MB: int = 2048
    DEFAULT_CPU_LIMIT_PERCENT: int = 100
    DEFAULT_PIDS_LIMIT: int = 256
    
    # Workspace
    WORKSPACE_BASE: Path = Path("/var/lib/linuxpilot")
    REAL_DATA_BASE: Path = Path.home()
    
    # Audit
    AUDIT_DIR: Path = Path("./audit")
    AUDIT_RETENTION_DAYS: int = 30
    
    # Metrics
    METRICS_ENABLED: bool = True
    METRICS_PORT: int = 9090
    
    # Authentication
    SECRET_KEY: str = "change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 1 week
    
    # CORS
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    
    # AT-SPI
    ATSPI_MAX_DEPTH: int = 25
    ATSPI_COMPRESSION_MAX_ELEMENTS: int = 80
    ATSPI_NAME_TRUNCATE: int = 60
    
    # Orchestrator budgets
    MAX_STEPS_PER_TASK: int = 60
    MAX_WALL_CLOCK_SECONDS: int = 600  # 10 minutes
    MAX_ROLLBACKS_PER_TASK: int = 3
    MAX_RETRIES_PER_STEP: int = 2
    MAX_REPLANS_PER_TASK: int = 2
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()
