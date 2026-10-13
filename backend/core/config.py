from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Resume Analyzer & Job Matching System"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_BASE_URL: str = "http://localhost:8000/api"

    # Database
    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/resume_analyzer"
    TEST_DATABASE_URL: str = "sqlite:///./test.db"

    # Redis & Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # Vector Store (ChromaDB)
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8000
    CHROMA_PERSIST_DIRECTORY: str = "./chroma_data"

    # LLM (Ollama)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2:3b"

    # File Storage & Limits
    TEMP_STORAGE_DIR: str = "./temp_storage"
    MAX_RESUME_SIZE_MB: int = 10
    MAX_ACCEPTED_RESUMES: int = 50
    TEMP_FILE_RETENTION_HOURS: int = 24
    WATCHDOG_INTERVAL_SECONDS: int = 300
    RESUME_CLAIM_TIMEOUT_SECONDS: int = 600
    EXPLANATION_TIMEOUT_SECONDS: int = 120

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

# Ensure temp directory exists
temp_path = Path(settings.TEMP_STORAGE_DIR)
temp_path.mkdir(parents=True, exist_ok=True)
