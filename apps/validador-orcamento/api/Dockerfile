# apps/validador-orcamento/api/Dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    # defaults sensatos (podem ser sobrescritos em docker run)
    OUTPUT_DIR=/app/output \
    DATA_DIR=/app/data \
    REDIS_URL=redis://redis:6379/1 \
    QUEUE_NAME=validador

WORKDIR /app

# deps Python
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# código
COPY src ./src

# diretórios padrão + usuário não-root
RUN mkdir -p /app/output /app/data && \
    adduser --system --no-create-home app && \
    chown -R app:app /app

USER app

EXPOSE 8000

# healthcheck leve (usa o próprio Python, sem instalar curl)
HEALTHCHECK --interval=30s --timeout=3s --retries=3 CMD python - <<'PY'
import json, urllib.request, sys
try:
    with urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=2) as r:
        j = json.load(r)
        sys.exit(0 if j.get("ok") else 1)
except Exception:
    sys.exit(1)
PY

CMD ["uvicorn","src.main:app","--host","0.0.0.0","--port","8000"]
