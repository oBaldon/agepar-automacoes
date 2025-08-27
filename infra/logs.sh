#!/usr/bin/env bash
set -Eeuo pipefail

# Use: ./logs.sh            -> segue api, worker, redis (todos)
#      ./logs.sh api        -> só api
#      ./logs.sh worker api -> múltiplos específicos

containers=( "$@" )
if [ ${#containers[@]} -eq 0 ]; then
  containers=( validador-api validador-worker redis )
fi

# Cores por container (ajuste à vontade)
color_for() {
  case "$1" in
    validador-api)    printf '\e[35m' ;; # magenta
    validador-worker) printf '\e[36m' ;; # ciano
    redis)            printf '\e[33m' ;; # amarelo
    *)                printf '\e[37m' ;; # cinza
  esac
}

pids=()
for c in "${containers[@]}"; do
  color="$(color_for "$c")"
  reset=$'\e[0m'
  (
    docker logs -f "$c" 2>&1 \
      | sed -u "s/^/[$c] /" \
      | awk -v c="$color" -v r="$reset" '{print c $0 r}'
  ) &
  pids+=($!)
done

trap 'for p in "${pids[@]}"; do kill $p 2>/dev/null || true; done' INT TERM
wait
