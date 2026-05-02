from rq import Queue

from app.workers.redis_conn import redis_conn


QUEUE_NAME = "paper_pilot"


def get_document_queue() -> Queue:
    return Queue(QUEUE_NAME, connection=redis_conn)
