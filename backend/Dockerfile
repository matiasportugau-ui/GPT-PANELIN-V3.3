# ==============================================================================
# Backend Service Dockerfile for Cloud Run deployment
# ==============================================================================
# Multi-stage build for optimized production image

# Stage 1: Builder
FROM python:3.11-slim AS builder

LABEL maintainer="GPT-PANELIN Team"
LABEL description="Backend Service for GCP Cloud Run with Cloud SQL integration"

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Stage 2: Production
FROM python:3.11-slim

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Create non-root user for security
RUN useradd -m -u 1000 -s /bin/bash panelin && \
    chown -R panelin:panelin /app

# Copy application code with proper ownership
COPY --chown=panelin:panelin . .

# Set environment variables
ENV PORT=8080 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Health check - verify service responds on /health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Switch to non-root user
USER panelin

# Expose port
EXPOSE 8080

# Run the application
CMD ["python", "main.py"]
