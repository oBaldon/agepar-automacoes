import os
from redis import from_url
from rq import Queue, Worker, Connection

def main():
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/1")
    qname = os.getenv("QUEUE_NAME", "validador")
    conn = from_url(redis_url)
    with Connection(conn):
        worker = Worker([Queue(qname)])
        worker.work(logging_level="INFO")

if __name__ == "__main__":
    main()
