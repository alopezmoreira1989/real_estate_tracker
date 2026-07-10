FROM python:3.12-slim AS builder

WORKDIR /build

COPY pyproject.toml ./
COPY src ./src

RUN pip install --no-cache-dir --prefix=/install .

FROM python:3.12-slim

RUN useradd --create-home --uid 1000 appuser

COPY --from=builder /install /usr/local

WORKDIR /app

# Alembic needs its own config + migration scripts at runtime (Phase 7: `serve` now touches the
# DB at startup via ensure_default_user, so migrations must actually run) — script_location in
# alembic.ini is relative to this directory, matching the repo layout.
COPY alembic.ini ./
COPY src/real_estate/infrastructure/persistence/migrations ./src/real_estate/infrastructure/persistence/migrations

# /data is where docker-compose mounts the SQLite volume; owned by appuser so a non-root
# container can create/write the DB file there.
RUN mkdir -p /data && chown -R appuser:appuser /app /data

USER appuser

CMD ["sh", "-c", "alembic upgrade head && python -m real_estate serve"]
