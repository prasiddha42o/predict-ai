"""PredictAI inference API -- FastAPI app factory."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import Base, engine
from app import models  # noqa: F401  (registers tables on Base.metadata)
from app.routers import machines

settings = get_settings()

app = FastAPI(
    title="PredictAI",
    description="Predictive maintenance & machine health inference API.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(machines.router)


@app.on_event("startup")
def create_tables_if_missing() -> None:
    # Convenience for local/SQLite dev only -- `alembic upgrade head` is the
    # real migration path (see docker-compose's backend entrypoint).
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
