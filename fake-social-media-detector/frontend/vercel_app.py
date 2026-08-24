"""Load FakeGuard FastAPI for Vercel when Root Directory is `frontend`."""

from __future__ import annotations

import sys
from pathlib import Path

FRONTEND = Path(__file__).resolve().parent
candidates = [
    FRONTEND / "server",
    FRONTEND.parent / "backend",
]
for path in candidates:
    if (path / "app" / "main.py").exists():
        sys.path.insert(0, str(path))
        break
else:
    raise RuntimeError("FakeGuard backend package was not found next to the frontend.")

from app.api.routes import analyze, compare, health, history, network, reports, samples  # noqa: E402
from app.main import app  # noqa: E402

for module in (health, analyze, history, compare, samples, reports, network):
    app.include_router(module.router)

__all__ = ["app"]
