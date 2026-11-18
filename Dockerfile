# ========================================================
# 金門地政雲 (Kinmen Land Cloud) - Production Dockerfile
# ========================================================
FROM python:3.11-slim

# Install system dependencies for GIS and PostgreSQL
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency definition and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Expose WebGIS application port
EXPOSE 8080

# Run database initialization and startup server
CMD ["sh", "-c", "python -m backend.init_db && uvicorn backend.app:app --host 0.0.0.0 --port 8080"]
