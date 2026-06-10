# Build context is the repo ROOT, not backend/ -- the app imports `ml/` (the
# same preprocessing code the notebooks use) and reads trained artifacts from
# `models/`, both siblings of backend/ rather than subdirectories of it.
# docker-compose's `build.context: ..` reflects that; `docker build backend/`
# will fail to find them.
FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
# CPU-only torch wheel -- the default PyPI wheel bundles CUDA libraries this
# container never uses, which is the difference between a ~200MB and a
# ~2.5GB `pip install`. Everything else installs from PyPI as normal.
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu \
    -r backend/requirements.txt

COPY ml/ ml/
COPY models/ models/
COPY backend/ backend/

WORKDIR /app/backend

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

# Migrate, then serve. `alembic upgrade head` is idempotent -- safe on every
# container start, not just the first one.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
