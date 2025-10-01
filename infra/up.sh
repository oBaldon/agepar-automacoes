#!/usr/bin/env bash
set -euo pipefail

# =========[ 0) Vars ]=========
ROOT="${ROOT:-$PWD}"

# Centralização: tudo em apps/validador-orcamento/shared
SHARED_ROOT="${SHARED_ROOT:-$ROOT/apps/validador-orcamento/shared}"
SHARED_DATA="${SHARED_DATA:-$SHARED_ROOT/data}"
SHARED_OUT="${SHARED_OUT:-$SHARED_ROOT/output}"

API_PORT="${API_PORT:-8001}"
API="http://localhost:${API_PORT}"
NETWORK="${NETWORK:-agepar-automacoes_default}"

# (opcional) iniciar o portal no final: export START_PORTAL=true
START_PORTAL="${START_PORTAL:-false}"

echo "ROOT=$ROOT"
echo "SHARED_DATA=$SHARED_DATA"
echo "SHARED_OUT=$SHARED_OUT"

# Garante diretórios (sem sudo)
mkdir -p "$SHARED_DATA" "$SHARED_OUT"

# (opcional, ajuda em ambientes com permissão chata)
# dá leitura/exec em pastas e leitura em arquivos pra qualquer usuário
chmod -R a+rX "$SHARED_ROOT" || true

# Dependências que usamos adiante
command -v docker >/dev/null || { echo "docker não encontrado"; exit 1; }
command -v jq >/dev/null || { echo "jq não encontrado (sudo apt-get install jq)"; exit 1; }
command -v curl >/dev/null || { echo "curl não encontrado"; exit 1; }

# =========[ 1) Network ]=========
docker network ls --format '{{.Name}}' | grep -qx "$NETWORK" || docker network create "$NETWORK"
echo "network: $NETWORK pronta"

# =========[ 2) Redis ]=========
docker rm -f redis 2>/dev/null || true
docker run -d --name redis --restart unless-stopped \
  --network "$NETWORK" \
  -p 6379:6379 \
  redis:7-alpine
echo "redis: ok"

# =========[ 3) Worker ]=========
cd "$ROOT/apps/validador-orcamento/worker"
docker build -t agepar/validador-worker:dev .
docker rm -f validador-worker 2>/dev/null || true
docker run -d --name validador-worker --restart unless-stopped \
  --network "$NETWORK" \
  -e REDIS_URL="redis://redis:6379/1" \
  -e QUEUE_NAME="validador" \
  -v "$SHARED_DATA:/app/data:ro" \
  -v "$SHARED_OUT:/app/output" \
  -u "$(id -u)":"$(id -g)" \
  agepar/validador-worker:dev
echo "worker: ok"

# =========[ 4) API ]=========
cd "$ROOT/apps/validador-orcamento/api"
docker build -t agepar/validador-api:dev .
docker rm -f validador-api 2>/dev/null || true

# CORS_ORIGINS dinâmico (IPs privados + localhost)
IPS="$(ip -4 -o addr show scope global 2>/dev/null \
  | awk '{split($4,a,"/"); ip=a[1];
          if (ip ~ /^10\./ || ip ~ /^192\.168\./ || ip ~ /^172\.(1[6-9]|2[0-9]|3[0-1])\./) print ip }')"
if [ -z "${IPS:-}" ]; then
  IPS="$(hostname -I 2>/dev/null | tr ' ' '\n' \
    | awk '($0 ~ /^10\./ || $0 ~ /^192\.168\./ || $0 ~ /^172\.(1[6-9]|2[0-9]|3[0-1])\./){print $0}')"
fi

ORIGINS=""
if [ -n "${IPS:-}" ]; then
  # gera "http://IP:5173," para cada IP e remove quebras de linha
  ORIGINS="$(printf 'http://%s:5173,' $IPS | tr -d '\n')"
fi
ORIGINS="${ORIGINS}http://localhost:5173,http://127.0.0.1:5173"
# remove vírgula final se existir
ORIGINS="${ORIGINS%,}"
echo ">> CORS_ORIGINS=${ORIGINS}"

# OBS: a API PRECISA ler de /app/data (somente leitura) e ESCREVER em /app/output.
# Se quiser manter seu mapeamento antigo, troque os :ro abaixo.
docker run -d --name validador-api --restart unless-stopped \
  --network "$NETWORK" \
  -p "${API_PORT}:8000" \
  -e REDIS_URL="redis://redis:6379/1" \
  -e QUEUE_NAME="validador" \
  -e CORS_ORIGINS="$ORIGINS" \
  -v "$SHARED_DATA:/app/data:ro" \
  -v "$SHARED_OUT:/app/output" \
  -u "$(id -u)":"$(id -g)" \
  agepar/validador-api:dev
echo "api: subida"

# =========[ 5) Portal (opcional) ]=========
if [ "${START_PORTAL}" = "true" ]; then
  echo "== Iniciando portal (pnpm dev) =="
  # garante pnpm (via corepack se existir)
  if ! command -v pnpm >/dev/null 2>&1; then
    if command -v corepack >/dev/null 2>&1; then
      corepack enable >/dev/null 2>&1 || true
      corepack prepare pnpm@latest --activate >/dev/null 2>&1 || true
    fi
  fi
  command -v pnpm >/dev/null 2>&1 || { echo "pnpm não encontrado (instale ou habilite corepack)"; exit 1; }

  export VITE_API_BASE="${API}"
  cd "$ROOT/apps/host"
  [ -d node_modules ] || pnpm install
  echo "Portal em http://localhost:5173 (VITE_API_BASE=$VITE_API_BASE)"
  exec pnpm dev -- --host 0.0.0.0 --port 5173
else
  echo "Portal NÃO iniciado (defina START_PORTAL=true para subir o Vite)."
fi

# =========[ 6) Health ]=========
echo "== Health =="
curl -s "${API}/health" | jq .
docker exec -it validador-api getent hosts redis || true
