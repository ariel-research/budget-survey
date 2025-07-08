# syntax=docker/dockerfile:1.4

##############################################
# Build stage
##############################################
FROM python:3.12-alpine AS builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies required for building Python packages
RUN apk update && apk upgrade && apk add --no-cache \
    build-base \
    gcc \
    g++ \
    libffi-dev \
    openssl-dev \
    libxml2-dev \
    libxslt-dev \
    zlib-dev \
    pkgconfig \
    cairo-dev \
    pango-dev \
    gdk-pixbuf-dev \
    shared-mime-info

# Create directory for wheels
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Build wheels for all dependencies
RUN --mount=type=cache,target=/root/.cache/pip \
    pip wheel --wheel-dir /app/wheels -r requirements.txt

##############################################
# Production stage
##############################################
FROM python:3.12-alpine AS production

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH="/app"

# Install runtime dependencies
RUN apk update && apk upgrade && apk add --no-cache \
    # Required for WeasyPrint (PDF generation)
    cairo \
    pango \
    gdk-pixbuf \
    shared-mime-info \
    # Required for MySQL connection
    mysql-dev \
    # Health check utilities
    curl \
    # Required for some Python packages
    libffi \
    openssl

# Create non-root user
RUN addgroup -g 1001 appuser && \
    adduser -u 1001 -G appuser -s /bin/sh -D appuser

# Set working directory
WORKDIR /app

# Copy wheels from builder stage
COPY --from=builder /app/wheels /tmp/wheels
COPY --from=builder /app/requirements.txt .

# Install Python packages from wheels
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-index --find-links /tmp/wheels -r requirements.txt && \
    rm -rf /tmp/wheels

# Copy application code
COPY --chown=appuser:appuser . .

# Create necessary directories and set permissions
RUN mkdir -p /app/logs /app/data && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 5001

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5001/health || exit 1

# Default command
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--workers", "4", "--worker-class", "sync", "--worker-tmp-dir", "/dev/shm", "--log-level", "info", "--access-logfile", "-", "--error-logfile", "-", "app:app"]

##############################################
# Development stage
##############################################
FROM production AS development

# Switch back to root for development tools installation
USER root

# Install development dependencies
RUN apk add --no-cache \
    git \
    vim \
    less

# Install development Python packages
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install pytest pytest-mock black ruff mypy pre-commit

# Switch back to appuser
USER appuser

# Override command for development
CMD ["python", "app.py"]