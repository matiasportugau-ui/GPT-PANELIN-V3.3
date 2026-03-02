FROM python:3.12-slim

WORKDIR /app

# Instalar dependencias primero (aprovechar cache de Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente
COPY . .

# Puerto por defecto de Cloud Run
EXPOSE 8080

# Ejecutar con uvicorn (async, producción)
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
