# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# (optional) system deps for builds; keep minimal
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl && \
    rm -rf /var/lib/apt/lists/*

# Install Python deps first for better layer caching
COPY requirements.txt .
RUN python -m pip install --upgrade pip && pip install -r requirements.txt

# Copy the app
COPY . .

EXPOSE 8000

# If your FastAPI app lives at app/api/main.py as `app`, this is correct:
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
