import os

from rq import SimpleWorker, Worker

from app.core.logging import configure_logging
from app.workers.queue import QUEUE_NAME
from app.workers.redis_conn import redis_conn


def main() -> None:
    configure_logging()
    worker_class = SimpleWorker if os.name == "nt" else Worker
    worker = worker_class([QUEUE_NAME], connection=redis_conn)
    worker.work()


if __name__ == "__main__":
    main()
