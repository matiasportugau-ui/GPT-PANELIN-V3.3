# ==============================================================================
# GPT-PANELIN-V3.2 Production Dockerfile
# ==============================================================================
# Multi-stage build for optimized production image

# Stage 1: Builder
FROM python:3.11-slim AS builder

LABEL maintainer="GPT-PANELIN Team"
LABEL description="GPT-PANELIN-V3.2 MCP Server"

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements files
COPY requirements.txt /app/
COPY mcp/requirements.txt /app/mcp/

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -r mcp/requirements.txt

# Stage 2: Production
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY mcp/ /app/mcp/
COPY mcp_tools/ /app/mcp_tools/
COPY background_tasks/ /app/background_tasks/
COPY panelin_reports/ /app/panelin_reports/
COPY openai_ecosystem/ /app/openai_ecosystem/

# Copy knowledge base files
COPY bromyros_pricing_master.json /app/
COPY bromyros_pricing_gpt_optimized.json /app/
COPY BMC_Base_Conocimiento_GPT-2.json /app/
COPY bom_rules.json /app/
COPY accessories_catalog.json /app/
COPY shopify_catalog_v1.json /app/
COPY corrections_log.json /app/
COPY bmc_logo.png /app/

# Copy additional necessary files
COPY quotation_calculator_v3.py /app/
COPY background_tasks_config.json /app/

# Create necessary directories
RUN mkdir -p /app/logs /app/panelin_reports/output && \
    chmod -R 755 /app/logs /app/panelin_reports/output

# Create non-root user for security
RUN useradd -m -u 1000 -s /bin/bash panelin && \
    chown -R panelin:panelin /app

# Switch to non-root user
USER panelin

# Expose MCP server port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import sys; from pathlib import Path; sys.exit(0 if Path('mcp/server.py').exists() else 1)"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MCP_SERVER_HOST=0.0.0.0 \
    MCP_SERVER_PORT=8000

# Entry point to run the MCP server
CMD ["python", "-m", "mcp.server"]
