"""FastAPI application factory for TEMFPA V.2."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from temfpa.config import settings


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="TEMFPA V.2 API",
        description="Football prediction and analysis API",
        version="2.0.0",
    )

    # --- CORS ---
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Startup: create DB tables ---
    @app.on_event("startup")
    def on_startup():
        from temfpa.db.base import Base
        from temfpa.db.session import engine
        Base.metadata.create_all(engine)

    # --- Health check ---
    @app.get("/api/v2/health")
    def health():
        return {"status": "ok", "version": "2.0.0"}

    # --- Mount routers ---
    from temfpa.api.routes.accuracy import router as accuracy_router
    from temfpa.api.routes.fixtures import router as fixtures_router
    from temfpa.api.routes.leagues import router as leagues_router
    from temfpa.api.routes.predict import router as predict_router
    from temfpa.api.routes.sync_trigger import router as sync_router
    from temfpa.api.routes.upcoming import router as upcoming_router

    app.include_router(leagues_router)
    app.include_router(fixtures_router)
    app.include_router(predict_router)
    app.include_router(upcoming_router)
    app.include_router(accuracy_router)
    app.include_router(sync_router)

    # --- Serve frontend static files ---
    frontend_dir = Path(__file__).parent.parent.parent.parent.parent / "frontend"
    if frontend_dir.exists():
        app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")

    return app


# Module-level app instance
app = create_app()
