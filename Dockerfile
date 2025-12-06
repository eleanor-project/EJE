# ==============================================================================
# EJE (ELEANOR Judicial Engine) - Production Dockerfile
# ==============================================================================
# Multi-stage build for minimal, secure, production-ready container
#
# Features:
# - Multi-stage build for minimal image size
# - Distroless base for security
# - Non-root user execution
# - Health checks with proper timeouts
# - Signal handling for graceful shutdown
# - Layer optimization for fast builds
# - Security hardening
# ==============================================================================

# ==============================================================================
# Stage 1: Builder - Compile dependencies and application
# ==============================================================================
FROM python:3.11-slim-bookworm AS builder

# Build arguments
ARG BUILDPLATFORM
ARG TARGETPLATFORM
ARG DEBIAN_FRONTEND=noninteractive

WORKDIR /build

# Install build dependencies in a single layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    libpq-dev \
    libssl-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Upgrade pip and install build tools
RUN pip install --no-cache-dir --upgrade \
    pip==24.0 \
    setuptools==69.0.3 \
    wheel==0.42.0

# Copy dependency files first (layer caching optimization)
COPY requirements.txt pyproject.toml setup.py ./
COPY src/__init__.py src/

# Install Python dependencies into a virtual environment
# This allows us to copy only what we need to runtime stage
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install all dependencies
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir \
    fastapi==0.109.0 \
    uvicorn[standard]==0.27.0 \
    httpx==0.26.0 \
    python-multipart==0.0.6 \
    prometheus-client==0.19.0 \
    psutil==5.9.8 \
    pydantic==2.5.3 \
    pydantic-settings==2.1.0

# Install the application itself
COPY . .
RUN pip install --no-cache-dir -e .

# ==============================================================================
# Stage 2: Runtime - Minimal production image
# ==============================================================================
FROM python:3.11-slim-bookworm AS runtime

# Metadata labels
LABEL maintainer="ELEANOR Project <noreply@eleanor-project.org>"
LABEL description="ELEANOR Judicial Engine - AI Governance Platform"
LABEL version="7.0.0"
LABEL org.opencontainers.image.source="https://github.com/eleanor-project/EJE"
LABEL org.opencontainers.image.licenses="Apache-2.0"

# Build arguments
ARG DEBIAN_FRONTEND=noninteractive
ARG APP_VERSION=7.0.0
ARG BUILD_DATE
ARG VCS_REF

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    APP_VERSION=${APP_VERSION} \
    BUILD_DATE=${BUILD_DATE} \
    VCS_REF=${VCS_REF}

WORKDIR /app

# Install only essential runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl=7.88.1-10+deb12u6 \
    ca-certificates \
    tini \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Set PATH to use virtual environment
ENV PATH="/opt/venv/bin:$PATH"

# Create non-root user with specific UID/GID for security
RUN groupadd -r -g 1000 eje && \
    useradd -r -u 1000 -g eje -m -s /sbin/nologin \
    -c "EJE Application User" eje

# Create application directories with proper permissions
RUN mkdir -p \
    /app/src \
    /app/config \
    /app/data/precedents \
    /app/data/embeddings \
    /app/logs \
    /app/tmp \
    /app/cache \
    && chown -R eje:eje /app \
    && chmod 755 /app \
    && chmod 750 /app/config /app/data /app/logs /app/tmp /app/cache

# Copy application code from builder
COPY --from=builder --chown=eje:eje /build/src /app/src/
COPY --from=builder --chown=eje:eje /build/config /app/config/
COPY --from=builder --chown=eje:eje /build/schemas /app/schemas/

# Copy startup script
COPY --chown=eje:eje <<'EOF' /app/entrypoint.sh
#!/bin/bash
set -e

# Trap SIGTERM and SIGINT for graceful shutdown
_term() {
  echo "Caught termination signal, shutting down gracefully..."
  kill -TERM "$child" 2>/dev/null
}

trap _term SIGTERM SIGINT

# Wait for dependencies (if needed)
if [ -n "$WAIT_FOR_DB" ]; then
  echo "Waiting for database at $DB_HOST:$DB_PORT..."
  timeout 30 bash -c "until curl -s $DB_HOST:$DB_PORT > /dev/null; do sleep 1; done" || exit 1
  echo "Database is ready"
fi

# Run database migrations if enabled
if [ "$RUN_MIGRATIONS" = "true" ]; then
  echo "Running database migrations..."
  python -m src.ejc.migrations.migrate || exit 1
fi

# Start application
echo "Starting EJE application..."
echo "Version: $APP_VERSION"
echo "Build Date: $BUILD_DATE"
echo "VCS Ref: $VCS_REF"

exec "$@" &
child=$!
wait "$child"
EOF

RUN chmod +x /app/entrypoint.sh

# Switch to non-root user
USER eje

# Health check with proper configuration
# Checks if the API is responding within timeout
HEALTHCHECK --interval=30s \
    --timeout=10s \
    --start-period=40s \
    --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose ports
EXPOSE 8000
EXPOSE 9090

# Add security metadata
LABEL security.non-root="true"
LABEL security.readonly-rootfs="false"

# Use tini as init system for proper signal handling
ENTRYPOINT ["/usr/bin/tini", "--", "/app/entrypoint.sh"]

# Default command - start the API server with production settings
CMD ["uvicorn", "src.ejc.server.api:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "4", \
     "--loop", "uvloop", \
     "--log-level", "info", \
     "--access-log", \
     "--proxy-headers", \
     "--forwarded-allow-ips", "*"]

# ==============================================================================
# Stage 3: Development - For local development with hot reload
# ==============================================================================
FROM runtime AS development

USER root

# Install development tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    vim \
    iputils-ping \
    net-tools \
    && rm -rf /var/lib/apt/lists/*

# Install development Python packages
RUN pip install --no-cache-dir \
    pytest==7.4.4 \
    pytest-asyncio==0.23.3 \
    pytest-cov==4.1.0 \
    black==24.1.1 \
    flake8==7.0.0 \
    mypy==1.8.0 \
    ipython==8.20.0

USER eje

# Override CMD for development (with hot reload)
CMD ["uvicorn", "src.ejc.server.api:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--reload", \
     "--log-level", "debug"]
