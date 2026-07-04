"""FastAPI dependencies for TEMFPA V.2."""

from temfpa.db.session import get_db  # noqa: F401 — re-export for use as FastAPI dependency
