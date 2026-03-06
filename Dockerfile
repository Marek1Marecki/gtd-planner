# ===============================
# Stage 1: builder
# ===============================
FROM python:3.14-slim-bookworm AS builder

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./

RUN UV_PROJECT_ENVIRONMENT=/opt/venv uv sync --no-dev --frozen

# ===============================
# Stage 2: runtime
# ===============================
FROM python:3.14-slim-bookworm

WORKDIR /app

# System dependencies for Django (no GDAL/PostGIS needed)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 10001 appuser

COPY --from=builder /opt/venv /opt/venv
COPY web/ /app/

ENV VIRTUAL_ENV="/opt/venv"
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=120s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/')"

USER appuser

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
