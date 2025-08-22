# src/runner.py
from __future__ import annotations
import os, time, sys, math, logging
from typing import List
from redis import Redis
from rq import Worker, Queue

REDIS_URL  = os.getenv("REDIS_URL",  "redis://redis:6379/1")
QUEUE_ENV  = os.getenv("QUEUE_NAME", "validador")
RQ_BURST   = os.getenv("RQ_BURST", "0").lower() in ("1", "true", "yes")
LOG_LEVEL  = os.getenv("LOG_LEVEL", "INFO").upper()
RQ_MAX_JOBS = int(os.getenv("RQ_MAX_JOBS", "0") or 0)  # 0 = ilimitado

logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO))

def _redis_conn() -> Redis:
    return Redis.from_url(
        REDIS_URL,
        socket_timeout=5,
        health_check_interval=30,
        retry_on_timeout=True,
    )

def wait_for_redis(timeout: int = 60) -> Redis:
    deadline = time.time() + timeout
    attempt = 0
    last_err = None
    while time.time() < deadline:
        try:
            conn = _redis_conn()
            conn.ping()
            logging.info("[runner] Conectado ao Redis: %s", REDIS_URL)
            return conn
        except Exception as e:
            last_err = e
            attempt += 1
            sleep_s = min(3, 0.3 * math.pow(1.8, attempt))
            logging.warning("[runner] Redis indisponível (%s). Tentando em %.1fs...", e, sleep_s)
            time.sleep(sleep_s)
    logging.error("[runner] Falha ao conectar no Redis após %ss: %s", timeout, last_err)
    sys.exit(1)

def main():
    conn = wait_for_redis(timeout=60)
    queue_names: List[str] = [q.strip() for q in QUEUE_ENV.split(",") if q.strip()]
    queues = [Queue(name, connection=conn) for name in queue_names]
    logging.info("[runner] Worker iniciado. Filas=%s burst=%s", queue_names, RQ_BURST)
    w = Worker(queues, connection=conn)
    # max_jobs só é usado se > 0
    kwargs = {"with_scheduler": True, "burst": RQ_BURST, "logging_level": getattr(logging, LOG_LEVEL, logging.INFO)}
    if RQ_MAX_JOBS > 0:
        kwargs["max_jobs"] = RQ_MAX_JOBS
    w.work(**kwargs)

if __name__ == "__main__":
    main()
