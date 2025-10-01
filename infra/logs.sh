#!/usr/bin/env bash
# logs.sh — segue logs de múltiplos containers com prefixo colorido e diagnóstico
# Uso:
#   ./logs.sh                  # tenta validador-{api,worker} e redis
#   ./logs.sh api              # casa por serviço/nome/substring
#   ./logs.sh '*validador*'    # glob
#   TAIL=200 SINCE=10m ./logs.sh
#   ./logs.sh -t 300 --since 1h api worker

set -Eeuo pipefail

DEFAULT=("validador-api" "validador-worker" "redis")

# --- flags curtinhas ---
FOLLOW=1
TAIL_DEFAULT="${TAIL:-100}"
TAIL="$TAIL_DEFAULT"
SINCE_ENV="${SINCE:-}"
SINCE_OPT=()
ARGS=()

while (( "$#" )); do
  case "$1" in
    -f|--follow) FOLLOW=1; shift ;;
    -t|--tail)   TAIL="$2"; shift 2 ;;
    --since)     SINCE_ENV="$2"; shift 2 ;;
    --no-follow) FOLLOW=0; shift ;;
    --) shift; while (( "$#" )); do ARGS+=("$1"); shift; done ;;
    -h|--help)
      echo "Uso: $0 [opções] [filtros...]"
      echo "  -f, --follow        seguir logs (default)"
      echo "  --no-follow         apenas imprimir o tail e sair"
      echo "  -t, --tail N        quantas linhas por container (default: $TAIL_DEFAULT)"
      echo "  --since DURAÇÃO     ex.: 10m, 1h, 2025-10-01T08:00:00"
      exit 0
      ;;
    *) ARGS+=("$1"); shift ;;
  esac
done

[[ -n "$SINCE_ENV" ]] && SINCE_OPT=(--since "$SINCE_ENV")
[[ ${#ARGS[@]} -eq 0 ]] && ARGS=("${DEFAULT[@]}")

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
for a in "${ARGS[@]}"; do
  # 1) exato
  for n in "${ALL_NAMES[@]}"; do
    [[ "$n" == "$a" ]] && resolved+=("$n") && continue 2
  done
  # 2) serviço do compose
  if (( compose_ok )) && [[ -n "${SERV2NAME[$a]:-}" ]]; then
    resolved+=("${SERV2NAME[$a]}"); continue
  fi
  # 3) glob (shell-like)
  if [[ "$a" == *"*"* || "$a" == *"?"* ]]; then
    pat="^$(printf '%s' "$a" | sed 's/[.[\^$()+{}|]/\\&/g; s/\*/.*/g; s/?/./g')$"
    while IFS= read -r n; do resolved+=("$n"); done < <(printf "%s\n" "${ALL_NAMES[@]}" | grep -iE "$pat" || true)
    [[ ${#resolved[@]} -gt 0 ]] && continue
  fi
  # 4) substring case-insensitive (pega todos)
  while IFS= read -r n; do resolved+=("$n"); done < <(printf "%s\n" "${ALL_NAMES[@]}" | grep -iF "$a" || true)
  [[ ${#resolved[@]} -gt 0 ]] || echo "[warn] não encontrei container para: $a" >&2
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

echo "[info] seguindo logs de: ${resolved[*]} (tail=$TAIL${SINCE_ENV:+ since=$SINCE_ENV})"
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
  local name="$1" c ts; c="$(color "$name")"
  ( set +e
    local first=1
    while docker ps -a --format '{{.Names}}' | grep -Fx -- "$name" >/dev/null; do
      (( first==0 )) && echo "[$name] (re)conectando aos logs..." >&2
      first=0
      cmd=(docker logs ${FOLLOW:+-f} --tail="$TAIL" "${SINCE_OPT[@]}" --timestamps "$name")
      if command -v stdbuf >/dev/null 2>&1; then
        stdbuf -oL -eL "${cmd[@]}" 2>&1 | awk -v pre="[$name] " -v c="$c" -v r="$reset" '{print c pre $0 r}'
      else
        "${cmd[@]}" 2>&1 | awk -v pre="[$name] " -v c="$c" -v r="$reset" '{print c pre $0 r}'
      fi
      # se saiu (container reiniciou ou logs fecharam), tenta de novo
      sleep 0.3
    done
    echo "[$name] finalizado."
  ) & pids+=($!)
}

for n in "${resolved[@]}"; do follow "$n"; done
trap 'for p in "${pids[@]:-}"; do kill $p 2>/dev/null || true; done' INT TERM EXIT
wait || true
