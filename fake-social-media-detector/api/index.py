"""Vercel serverless entry — serves FastAPI at /api/* on the same domain as the UI."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.api.routes import analyze, compare, health, history, network, reports, samples  # noqa: E402
from app.main import app  # noqa: E402

# Vercel may forward "/api/health" or strip the prefix to "/health".
# Register both so the frontend's /api/* calls succeed.
for module in (health, analyze, history, compare, samples, reports, network):
    app.include_router(module.router)

__all__ = ["app"]
