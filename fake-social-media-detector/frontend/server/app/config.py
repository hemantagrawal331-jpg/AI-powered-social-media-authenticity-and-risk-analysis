"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings

APP_DIR = Path(__file__).resolve().parent
BACKEND_DIR = APP_DIR.parent
REPO_DIR = BACKEND_DIR.parent
IS_VERCEL = bool(os.environ.get("VERCEL"))
WRITABLE_DIR = Path("/tmp/fakeguard") if IS_VERCEL else BACKEND_DIR


def _first_existing_samples() -> Path:
    candidates = [
        REPO_DIR / "data" / "samples",
        BACKEND_DIR / "data" / "samples",
    ]
    for path in candidates:
        if (path / "accounts.json").exists():
            return path
    return candidates[0]


SAMPLES_DIR = _first_existing_samples()
UPLOAD_DIR = WRITABLE_DIR / "uploads"
REPORT_DIR = WRITABLE_DIR / "reports"


class Settings(BaseSettings):
    app_name: str = "FakeGuard AI"
    app_version: str = "1.0.0"
    api_prefix: str = "/api"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    database_url: str = ""
    max_upload_bytes: int = 2 * 1024 * 1024  # 2 MB
    max_image_bytes: int = 1 * 1024 * 1024  # 1 MB
    history_limit: int = 200

    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        if IS_VERCEL:
            return f"sqlite:///{WRITABLE_DIR / 'fakeguard.db'}"
        return "sqlite:///./fakeguard.db"


@lru_cache
def get_settings() -> Settings:
    for path in (UPLOAD_DIR, REPORT_DIR, WRITABLE_DIR):
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
    return Settings()
