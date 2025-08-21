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
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# ---- código
COPY src ./src

# ---- dirs de trabalho
RUN mkdir -p /app/data /app/output

# ---- envs default (podem ser sobrescritos no run)
ENV QUEUE_NAME=validador \
    REDIS_URL=redis://redis:6379/1

# (opcional) sinal mais amigável p/ parada
STOPSIGNAL SIGTERM

# (opcional) healthcheck simples: verifica se o Redis está acessível
HEALTHCHECK --interval=30s --timeout=3s --retries=3 CMD \
  python -c "from redis import Redis; import os,sys; \
r=Redis.from_url(os.getenv('REDIS_URL','redis://redis:6379/1')); \
r.ping() or sys.exit(1)" || exit 1

# ---- inicia o worker programaticamente (o runner já espera o Redis)
ENTRYPOINT ["python","-m","src.runner"]
