#!/usr/bin/env bash
set -Eeuo pipefail

# --- helpers ---
here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
root="$(cd "$here/.." && pwd)"

# Carrega .env (se existir) e define defaults
if [[ -f "$here/.env" ]]; then set -a; source "$here/.env"; set +a; fi

PROJECT="${PROJECT:-agepar-automacoes}"
NETWORK="${NETWORK:-${PROJECT}_default}"

IMG_API="${IMG_API:-agepar/validador-api:dev}"
IMG_WORKER="${IMG_WORKER:-agepar/validador-worker:dev}"

ROOT="${ROOT:-$root}"
SHARED_ROOT="${SHARED_ROOT:-$ROOT/apps/validador-orcamento/shared}"
SHARED_DATA="${SHARED_DATA:-$SHARED_ROOT/data}"
SHARED_OUT="${SHARED_OUT:-$SHARED_ROOT/output}"

QUEUE_NAME="${QUEUE_NAME:-validador}"
REDIS_URL="${REDIS_URL:-redis://redis:6379/1}"
REDIS_PORT="${REDIS_PORT:-6379}"

API_PORT="${API_PORT:-8001}"
MAX_UPLOAD_MB="${MAX_UPLOAD_MB:-200}"

API_BASE="http://localhost:${API_PORT}"

# Dependências básicas
command -v docker >/dev/null || { echo "docker não encontrado"; exit 1; }
command -v jq >/dev/null || { echo "jq não encontrado (sudo apt-get install jq)"; exit 1; }

echo "ROOT=$ROOT"
echo "SHARED_DATA=$SHARED_DATA"
echo "SHARED_OUT=$SHARED_OUT"
mkdir -p "$SHARED_DATA" "$SHARED_OUT"

# Permissões (facilitam vida quando rodando com -u uid:gid)
# leitura/exec em pastas; leitura nos arquivos; escrita fica com seu usuário
chmod -R a+rX "$SHARED_ROOT" || true

# --- 1) network ---
if ! docker network ls --format '{{.Name}}' | grep -qx "$NETWORK"; then
  docker network create "$NETWORK"
fi

# --- 2) redis ---
docker rm -f redis 2>/dev/null || true
docker run -d --name redis --restart unless-stopped \
  --network "$NETWORK" \
  -p "${REDIS_PORT}:6379" \
  redis:7-alpine

# --- 3) worker ---
(
  cd "$ROOT/apps/validador-orcamento/worker"
  docker build -t "$IMG_WORKER" .
)
docker rm -f validador-worker 2>/dev/null || true
docker run -d --name validador-worker --restart unless-stopped \
  --network "$NETWORK" \
  -e REDIS_URL="$REDIS_URL" \
  -e QUEUE_NAME="$QUEUE_NAME" \
  -v "$SHARED_DATA:/app/data:ro" \
  -v "$SHARED_OUT:/app/output" \
  -u "$(id -u)":"$(id -g)" \
  "$IMG_WORKER"

# --- 4) api ---
(
  cd "$ROOT/apps/validador-orcamento/api"
  docker build -t "$IMG_API" .
)

# Descobre IPs locais para CORS (privados + localhost)
IPS="$(ip -4 -o addr show scope global 2>/dev/null \
  | awk '{split($4,a,"/"); ip=a[1];
          if (ip ~ /^10\./ || ip ~ /^192\.168\./ || ip ~ /^172\.(1[6-9]|2[0-9]|3[0-1])\./) print ip }' \
  | tr '\n' ' ')"
if [[ -z "${IPS// }" ]]; then
  IPS="$(hostname -I 2>/dev/null | tr ' ' '\n' \
    | awk '($0 ~ /^10\./ || $0 ~ /^192\.168\./ || $0 ~ /^172\.(1[6-9]|2[0-9]|3[0-1])\./){print $0}' \
    | tr '\n' ' ')"
fi

ORIGINS=""
for ip in $IPS; do
  ORIGINS="${ORIGINS}http://${ip}:5173,"
done
ORIGINS="${ORIGINS}http://localhost:5173,http://127.0.0.1:5173"
ORIGINS="${ORIGINS%,}"
echo ">> CORS_ORIGINS=${ORIGINS}"

docker rm -f validador-api 2>/dev/null || true
docker run -d --name validador-api --restart unless-stopped \
  --network "$NETWORK" \
  -p "${API_PORT}:8000" \
  -e REDIS_URL="$REDIS_URL" \
  -e QUEUE_NAME="$QUEUE_NAME" \
  -e CORS_ORIGINS="$ORIGINS" \
  -e MAX_UPLOAD_MB="$MAX_UPLOAD_MB" \
  -v "$SHARED_DATA:/app/data" \
  -v "$SHARED_OUT:/app/output:ro" \
  -u "$(id -u)":"$(id -g)" \
  "$IMG_API"

# --- 5) health ---
sleep 1
echo "== Health =="
curl -fsS "$API_BASE/health" | jq . || true
docker exec -it validador-api getent hosts redis || true

echo
echo "Tudo no ar! API: $API_BASE"
echo "Uploads: POST $API_BASE/upload (form-data: file=@...; subdir=uploads/jobX)"
echo "Jobs:    POST $API_BASE/jobs"
