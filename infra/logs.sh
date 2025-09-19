#!/usr/bin/env bash
# logs.sh — segue logs de múltiplos containers com prefixo colorido e diagnóstico
# Uso:
#   ./logs.sh                  # tenta validador-{api,worker} e redis
#   ./logs.sh api              # casa por serviço/nome/substring
#   ./logs.sh '*validador*'    # glob
# Vars:
#   TAIL=200 SINCE=10m ./logs.sh

set -Eeuo pipefail

DEFAULT=("validador-api" "validador-worker" "redis")
TAIL="${TAIL:-100}"
SINCE_OPT=()
[[ -n "${SINCE:-}" ]] && SINCE_OPT=(--since "$SINCE")

args=("$@")
[[ ${#args[@]} -eq 0 ]] && args=("${DEFAULT[@]}")

# --- coleta nomes conhecidos (docker global)
mapfile -t ALL_NAMES < <(docker ps -a --format '{{.Names}}')

# --- tenta mapear serviços do docker compose (no diretório do projeto)
compose_ok=0
declare -A SERV2NAME
if docker compose version &>/dev/null; then
  mapfile -t COMPOSE_IDS < <(docker compose ps -q 2>/dev/null || true)
  if [[ ${#COMPOSE_IDS[@]} -gt 0 ]]; then
    compose_ok=1
    for id in "${COMPOSE_IDS[@]}"; do
      name="$(docker inspect -f '{{.Name}}' "$id" | sed 's#^/##')"
      svc="$(docker inspect -f '{{index .Config.Labels "com.docker.compose.service"}}' "$id")"
      [[ -n "$name" ]] && ALL_NAMES+=("$name")
      [[ -n "$svc" && -n "$name" ]] && SERV2NAME["$svc"]="$name"
    done
  fi
fi

# --- resolve cada arg p/ um container
resolved=()
for a in "${args[@]}"; do
  # 1) exato
  for n in "${ALL_NAMES[@]}"; do
    [[ "$n" == "$a" ]] && resolved+=("$n") && continue 2
  done
  # 2) serviço do compose
  if (( compose_ok )) && [[ -n "${SERV2NAME[$a]:-}" ]]; then
    resolved+=("${SERV2NAME[$a]}"); continue
  fi
  # 3) glob
  if [[ "$a" == *"*"* || "$a" == *"?"* ]]; then
    while IFS= read -r n; do resolved+=("$n"); done < <(printf "%s\n" "${ALL_NAMES[@]}" | grep -F . | grep -i -E "$(printf '%s' "$a" | sed 's/\*/.*/g; s/?/./g')" || true)
    [[ ${#resolved[@]} -gt 0 ]] && continue
  fi
  # 4) substring case-insensitive (pega o primeiro)
  match="$(printf "%s\n" "${ALL_NAMES[@]}" | grep -iF "$a" | head -n1 || true)"
  if [[ -n "$match" ]]; then
    resolved+=("$match")
  else
    echo "[warn] não encontrei container para: $a" >&2
  fi
done

# de-dup
declare -A seen; uniq=()
for n in "${resolved[@]}"; do [[ -z "${seen[$n]:-}" ]] && uniq+=("$n") && seen[$n]=1; done
resolved=("${uniq[@]}")

if [[ ${#resolved[@]} -eq 0 ]]; then
  echo "[info] nenhum container resolvido."
  echo "       Dica: 'docker ps --format \"table {{.Names}}\t{{.Status}}\"' ou 'docker compose ps'"
  exit 0
fi

echo "[info] seguindo logs de: ${resolved[*]} (tail=$TAIL)"
is_tty=0; [[ -t 1 ]] && is_tty=1
reset=$'\e[0m'
color() {
  [[ $is_tty -eq 1 ]] || { printf ''; return; }
  case "$1" in
    *validador-api*)    printf '\e[35m' ;; # magenta
    *validador-worker*) printf '\e[36m' ;; # ciano
    *redis*)            printf '\e[33m' ;; # amarelo
    *)                  printf '\e[37m' ;; # cinza
  esac
}

pids=()
follow() {
  local name="$1" c; c="$(color "$name")"
  ( set +e
    while docker ps -a --format '{{.Names}}' | grep -Fx -- "$name" >/dev/null; do
      if command -v stdbuf >/dev/null 2>&1; then
        stdbuf -oL -eL docker logs -f --tail="$TAIL" "${SINCE_OPT[@]}" "$name" 2>&1 \
          | awk -v pre="[$name] " -v c="$c" -v r="$reset" '{print c pre $0 r}'
      else
        docker logs -f --tail="$TAIL" "${SINCE_OPT[@]}" "$name" 2>&1 \
          | awk -v pre="[$name] " -v c="$c" -v r="$reset" '{print c pre $0 r}'
      fi
      sleep 0.3
    done
    echo "[$name] finalizado."
  ) & pids+=($!)
}

for n in "${resolved[@]}"; do follow "$n"; done
trap 'for p in "${pids[@]:-}"; do kill $p 2>/dev/null || true; done' INT TERM EXIT
wait || true

