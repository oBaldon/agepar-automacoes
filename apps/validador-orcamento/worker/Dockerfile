# apps/validador-orcamento/worker/Dockerfile
FROM python:3.12-slim

# ---- ambiente básico
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    TZ=UTC \
    PYTHONPATH=/app

WORKDIR /app

# ---- deps (camada cacheável)
COPY requirements.txt .
RUN python -m pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ---- código
COPY src ./src

# ---- dirs de trabalho + usuário não-root
RUN set -eux; \
    mkdir -p /app/output /app/data; \
    groupadd -r app; \
    useradd -r -g app -d /nonexistent -s /usr/sbin/nologin app; \
    chown -R app:app /app
USER app

# ---- envs default (podem ser sobrescritos no run)
ENV QUEUE_NAME=validador \
    REDIS_URL=redis://redis:6379/1

STOPSIGNAL SIGTERM

# ---- healthcheck simples: verifica Redis
HEALTHCHECK --interval=30s --timeout=3s --retries=3 CMD \
  ["python","-c","import os,sys; from redis import Redis; r=Redis.from_url(os.getenv('REDIS_URL','redis://redis:6379/1')); r.ping() or sys.exit(1)"]

# ---- inicia o worker
ENTRYPOINT ["python","-m","src.runner"]
