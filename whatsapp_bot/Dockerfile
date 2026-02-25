# ==============================================================================
# WhatsApp Bot - Cognitive Real Estate Assistant
# Dockerfile for Google Cloud Run deployment
# ==============================================================================
# Fix C2: Maintains package structure for relative imports
# COPY . /app/whatsapp_bot/ (not /app/) so 'from .config import ...' works

FROM python:3.11-slim

LABEL maintainer="GPT-PANELIN Team"
LABEL description="BMC Uruguay WhatsApp Bot - Panel Quotation Assistant with OpenAI + Firestore"

WORKDIR /app

# Install runtime dependencies (curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (copy requirements first for layer caching)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /app/requirements.txt

# Copy application code INTO the package directory (Fix C2)
# This preserves whatsapp_bot/ as a Python package so relative imports work
COPY . /app/whatsapp_bot/

# Create non-root user (matches existing repo convention: panelin, uid 1000)
RUN useradd -m -u 1000 -s /bin/bash panelin \
    && chown -R panelin:panelin /app

USER panelin

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

# uvicorn with package path (Fix C2: whatsapp_bot.app:app not app:app)
# 2 workers: sufficient for I/O-bound webhooks, lower memory footprint
CMD ["uvicorn", "whatsapp_bot.app:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "2"]
