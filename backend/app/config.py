"""Application settings and the path bootstrap that lets the backend import `ml/`.

`ml/` is the repo's single source of truth for preprocessing (see
`ml/preprocessing/tabular.py`'s docstring). The backend is a sibling directory
of it, not a subpackage, so the project root has to be on `sys.path` before
anything imports `ml.*` -- exactly the same bootstrap every notebook does with
`sys.path.insert(0, str(ROOT))`. Doing it here, once, at import time of the
lowest-level app module means every other module can just `import ml.data`
without repeating it.
"""

from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path

# backend/app/config.py -> backend/app -> backend -> project root
ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT_DIR / "backend"
MODELS_DIR = ROOT_DIR / "models"

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from pydantic_settings import BaseSettings, SettingsConfigDict  # noqa: E402


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    database_url: str = "sqlite:///./predictai.db"
    simulator_interval_seconds: float = 3.0
    frontend_origin: str = "http://localhost:3000"


@lru_cache
def get_settings() -> Settings:
    return Settings()
