# Frontend Dockerfile for Cloud Run deployment
# Base image: Python 3.9 slim
FROM python:3.9-slim-buster

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variable for port
ENV PORT 8080

# Run the application
CMD ["python", "main.py"]
