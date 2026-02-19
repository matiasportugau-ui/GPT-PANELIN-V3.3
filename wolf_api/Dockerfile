# ==============================================================================
# Wolf API Dockerfile
# ==============================================================================
# FastAPI backend for Panelin Knowledge Base operations

FROM python:3.11-slim

LABEL maintainer="GPT-PANELIN Team"
LABEL description="Panelin Wolf API - Knowledge Base Backend"

# Set working directory
WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /app/

# Create non-root user for security
RUN useradd -m -u 1000 -s /bin/bash panelin && \
    chown -R panelin:panelin /app

# Switch to non-root user
USER panelin

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
