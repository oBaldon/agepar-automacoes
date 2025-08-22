# apps/validador-orcamento/api/Dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    OUTPUT_DIR=/app/output \
    DATA_DIR=/app/data \
    REDIS_URL=redis://redis:6379/1 \
    QUEUE_NAME=validador

WORKDIR /app

# Dependências
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Código
COPY src ./src

# Diretórios padrão + usuário não-root (cria grupo e usuário explicitamente)
RUN set -eux; \
    mkdir -p /app/output /app/data; \
    groupadd -r app; \
    useradd -r -g app -d /nonexistent -s /usr/sbin/nologin app; \
    chown -R app:app /app

USER app

EXPOSE 8000

# Healthcheck leve (sem heredoc)
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD ["python","-c","import json,urllib.request,sys; \
r=urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2); \
j=json.load(r); sys.exit(0 if j.get('ok') else 1)"]

CMD ["uvicorn","src.main:app","--host","0.0.0.0","--port","8000"]
