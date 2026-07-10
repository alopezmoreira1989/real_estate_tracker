FROM python:3.12-slim AS builder

WORKDIR /build

COPY pyproject.toml ./
COPY src ./src

RUN pip install --no-cache-dir --prefix=/install .

FROM python:3.12-slim

RUN useradd --create-home --uid 1000 appuser

COPY --from=builder /install /usr/local

WORKDIR /app

USER appuser

CMD ["python", "-m", "real_estate", "serve"]
