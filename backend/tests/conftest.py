"""Shared pytest fixtures.

DATABASE_URL must be set before `app.db` is first imported anywhere (it opens
the engine at module import time), so this file sets it before importing
anything from `app`. Every test gets a clean schema via drop-then-create on
the one shared engine, rather than a fresh SQLite file per test -- the engine
itself is a process-wide singleton once imported.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("DATABASE_URL", f"sqlite:///{BACKEND_DIR}/test_predictai.db")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
