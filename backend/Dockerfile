# Jarvis backend image.
FROM python:3.11-slim

# Don't buffer stdout/stderr; no .pyc files.
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install deps first so the layer caches across code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Migrations are applied at startup by docker-compose; this default just serves.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
