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
# (opcional) se não usa mais, remova a cópia de 'scripts'
# COPY scripts ./scripts

# 3) dirs de trabalho
RUN mkdir -p /app/data /app/output

# 4) (opcional, mas útil) timezone fixo para gerar 'generated_at' em -03:00
# RUN apt-get update && apt-get install -y --no-install-recommends tzdata && \
#     ln -fs /usr/share/zoneinfo/America/Sao_Paulo /etc/localtime && \
#     dpkg-reconfigure -f noninteractive tzdata && \
#     rm -rf /var/lib/apt/lists/*
# ENV TZ=America/Sao_Paulo

# 5) Entrypoint em modo CLI (aceita subcomandos 'precos-auto' e 'estrutura-auto')
ENTRYPOINT ["python","-m","src.cli"]
CMD ["--help"]
