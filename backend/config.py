from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "AI Course Project Evaluator"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/ai_course_evaluator"
    cors_origins: list[str] = ["http://localhost:5173"]

    upload_dir: Path = Path("backend/data/uploads")
    faiss_dir: Path = Path("backend/data/faiss")
    reports_dir: Path = Path("backend/data/reports")

    llm_api_key: str = ""
    llm_api_base: str | None = "https://generativelanguage.googleapis.com/v1beta/openai/"
    llm_chat_model: str = "gemini-2.5-flash"
    llm_embedding_model: str = "gemini-embedding-001"

    chunk_word_size: int = 700
    chunk_word_overlap: int = 120
    retrieval_top_k: int = 5
    plagiarism_threshold: float = 0.92

    demo_teacher_name: str = "Course Admin"
    demo_teacher_email: str = "teacher@example.com"
    demo_teacher_password: str = "teach123"
    auto_seed_demo_students: bool = True

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    def ensure_directories(self) -> None:
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.faiss_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_directories()
    return settings
