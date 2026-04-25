# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install optional production dependencies
RUN pip install --no-cache-dir gunicorn redis psycopg2-binary

# Copy the rest of the application
COPY . .

# Create necessary directories
RUN mkdir -p storage/uploads storage/reports storage/exports \
    storage/tmp storage/logs storage/task_results storage/repos

# Expose the port
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]