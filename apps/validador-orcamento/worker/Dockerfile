FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONPATH=/app

WORKDIR /app

# 1) deps
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# 2) código
COPY src ./src
COPY scripts ./scripts

# 3) dirs de trabalho (onde seus jobs leem/escrevem)
RUN mkdir -p /app/data /app/output

# 4) envs padrão (pode sobrescrever em runtime)
ENV QUEUE_NAME=validador \
    REDIS_URL=redis://redis:6379/1

# 5) entra no runner programático do RQ (sem Click, sem warnings)
ENTRYPOINT ["python","-m","src.runner"]
