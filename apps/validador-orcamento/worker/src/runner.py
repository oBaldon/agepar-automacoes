# src/runner.py
from __future__ import annotations
import os, time, sys, math
from typing import List
from redis import Redis
from rq import Worker, Queue

REDIS_URL  = os.getenv("REDIS_URL",  "redis://redis:6379/1")
QUEUE_ENV  = os.getenv("QUEUE_NAME", "validador")
RQ_BURST   = os.getenv("RQ_BURST", "0") in ("1", "true", "True")

def _redis_conn() -> Redis:
    return Redis.from_url(
        REDIS_URL,
        socket_timeout=5,
        health_check_interval=30,
        retry_on_timeout=True,
    )

def wait_for_redis(timeout: int = 60) -> Redis:
    """
    Tenta conectar + PING no Redis até 'timeout' (com backoff).
    Evita crash-loop quando Redis ainda não está pronto.
    """
    deadline = time.time() + timeout
    attempt = 0
    last_err = None

    while time.time() < deadline:
        try:
            conn = _redis_conn()
            conn.ping()
            print(f"[runner] Conectado ao Redis: {REDIS_URL}", flush=True)
            return conn
        except Exception as e:
            last_err = e
            attempt += 1
            # backoff exponencial (máx 3s)
            sleep_s = min(3, 0.3 * math.pow(1.8, attempt))
            print(f"[runner] Redis indisponível ({e}). Tentando em {sleep_s:.1f}s...", flush=True)
            time.sleep(sleep_s)

    print(f"[runner] Falha ao conectar no Redis após {timeout}s: {last_err}", flush=True)
    sys.exit(1)

def main():
    conn = wait_for_redis(timeout=60)

    queue_names: List[str] = [q.strip() for q in QUEUE_ENV.split(",") if q.strip()]
    queues = [Queue(name, connection=conn) for name in queue_names]

    print(f"[runner] Worker iniciado. Filas={queue_names} burst={RQ_BURST}", flush=True)
    w = Worker(queues, connection=conn)
    # with_scheduler=True agenda requeues/cleanups de forma automática
    w.work(with_scheduler=True, burst=RQ_BURST)

if __name__ == "__main__":
    main()
