FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY server/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY server .

RUN mkdir -p /app/history

EXPOSE 8000

ENV PYTHONUNBUFFERED=1

CMD ["sh", "-c", "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
