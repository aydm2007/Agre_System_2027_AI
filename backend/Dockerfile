# [AGRI-GUARDIAN] Production Dockerfile for AgriAsset V21 Backend
FROM python:3.11-slim-bullseye AS builder

WORKDIR /app

# Install system dependencies required for psycopg2 and compiling packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# ----------------- Final Stage -----------------
FROM python:3.11-slim-bullseye

WORKDIR /app/backend

# Install runtime package dependencies 
# curl used for healthchecks (probe)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    gettext \
    && rm -rf /var/lib/apt/lists/*

# Copy wheels from builder and install
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache /wheels/*

# Copy the backend codebase
COPY ./backend /app/backend

# Copy and prepare entrypoint
COPY ./backend/scripts/entrypoint.sh /app/backend/entrypoint.sh
RUN chmod +x /app/backend/entrypoint.sh

# Environment defaults
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE="core_project.settings"

EXPOSE 8000

ENTRYPOINT ["/app/backend/entrypoint.sh"]
