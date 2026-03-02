FROM python:3.12-slim AS base

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY templates/ templates/
COPY src/ src/

ENV PYTHONPATH=/app/src
EXPOSE 8080

CMD ["uvicorn", "panelin_sheets_orchestrator.service:app", "--host", "0.0.0.0", "--port", "8080"]
