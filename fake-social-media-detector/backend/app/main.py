"""FakeGuard AI FastAPI application entrypoint."""

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import analyze, compare, health, history, network, reports, samples
from app.config import get_settings
from app.database.session import Base, engine

settings = get_settings()
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Heuristic social-media authenticity and risk analysis prototype.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix=settings.api_prefix)
app.include_router(analyze.router, prefix=settings.api_prefix)
app.include_router(history.router, prefix=settings.api_prefix)
app.include_router(compare.router, prefix=settings.api_prefix)
app.include_router(samples.router, prefix=settings.api_prefix)
app.include_router(reports.router, prefix=settings.api_prefix)
app.include_router(network.router, prefix=settings.api_prefix)


@app.exception_handler(Exception)
async def unhandled_error(_: Request, exc: Exception) -> JSONResponse:
    if isinstance(exc, (HTTPException, RequestValidationError)):
        raise exc
    return JSONResponse(status_code=500, content={"detail": "An unexpected server error occurred."})


@app.get("/")
def root() -> dict:
    return {
        "name": settings.app_name,
        "docs": "/docs",
        "health": f"{settings.api_prefix}/health",
    }
