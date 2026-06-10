"""PredictAI inference API -- FastAPI app factory."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import Base, engine
from app import models  # noqa: F401  (registers tables on Base.metadata)
from app.routers import alerts, machines, maintenance, predictions
from app.ws import router as ws_router, simulator_loop

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Convenience for local/SQLite dev only -- `alembic upgrade head` is the
    # real migration path (see docker-compose's backend entrypoint).
    Base.metadata.create_all(bind=engine)
    task = asyncio.create_task(simulator_loop())
    try:
        yield
    finally:
        task.cancel()


app = FastAPI(
    title="PredictAI",
    description="Predictive maintenance & machine health inference API.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(machines.router)
app.include_router(predictions.router)
app.include_router(alerts.router)
app.include_router(maintenance.router)
app.include_router(ws_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
