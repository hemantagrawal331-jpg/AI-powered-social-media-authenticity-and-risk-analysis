"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings


ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
SAMPLES_DIR = DATA_DIR / "samples"
UPLOAD_DIR = ROOT_DIR / "backend" / "uploads"
REPORT_DIR = ROOT_DIR / "backend" / "reports"


class Settings(BaseSettings):
    app_name: str = "FakeGuard AI"
    app_version: str = "1.0.0"
    api_prefix: str = "/api"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    database_url: str = "sqlite:///./fakeguard.db"
    max_upload_bytes: int = 2 * 1024 * 1024  # 2 MB
    max_image_bytes: int = 1 * 1024 * 1024  # 1 MB
    history_limit: int = 200

    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    return Settings()
