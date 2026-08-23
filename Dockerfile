FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV OLLAMA_HOST=http://localhost:11434
ENV OLLAMA_MODEL=llama3.1:8b
ENV CAMPAIGN_STORE_PATH=/app/campaigns
ENV VECTOR_STORE_PATH=/app/faiss_db

WORKDIR /app

COPY pyproject.toml .
COPY backend ./backend
COPY frontend ./frontend
COPY docs ./docs
COPY .env.example .env

RUN pip install --no-cache-dir ".[dev]"

EXPOSE 8000

CMD ["python", "-m", "backend.app"]
