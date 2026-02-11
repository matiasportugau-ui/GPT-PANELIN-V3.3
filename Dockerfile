# Dockerfile for GPT-PANELIN-V3.2 with BOOT architecture
#
# This Dockerfile demonstrates how to integrate the BOOT process
# into a container environment.
#
# Build:
#   docker build -t gpt-panelin-v3.2 .
#
# Run:
#   docker run -v /path/to/knowledge:/app/knowledge_src gpt-panelin-v3.2
#
# Run with embeddings (requires API key):
#   docker run -e GENERATE_EMBEDDINGS=1 -e OPENAI_API_KEY=sk-... gpt-panelin-v3.2

FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    bash \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy application files
COPY requirements.txt .
COPY boot.sh .
COPY boot_preload.py .
COPY index_validator.py .
COPY README_BOOT_INTEGRATION.md .

# Copy application code (add your app files here)
# COPY your_app/ ./your_app/
# COPY *.py .
# COPY *.json .

# Create directories
RUN mkdir -p knowledge_src knowledge

# Make scripts executable
RUN chmod +x boot.sh boot_preload.py index_validator.py

# Environment variables (embeddings disabled by default)
ENV GENERATE_EMBEDDINGS=0
ENV PYTHON_BIN=python3
ENV VENV_DIR=/app/.venv

# Pre-create virtual environment for faster startup
RUN python3 -m venv ${VENV_DIR} && \
    ${VENV_DIR}/bin/pip install --upgrade pip && \
    ${VENV_DIR}/bin/pip install -r requirements.txt

# Volume for knowledge source files
VOLUME ["/app/knowledge_src"]

# Health check - verify BOOT completed
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD test -f .boot-ready || exit 1

# Run BOOT on container start
ENTRYPOINT ["./boot.sh"]

# Default command (can be overridden)
CMD []
