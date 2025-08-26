#!/usr/bin/env bash
set -euo pipefail
docker rm -f validador-api 2>/dev/null || true
docker rm -f validador-worker 2>/dev/null || true
docker rm -f redis 2>/dev/null || true
echo "Containers removidos."
