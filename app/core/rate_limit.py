from __future__ import annotations

import time

from app.core.config import get_settings
from app.workers.redis_conn import redis_conn


class RateLimitError(Exception):
    pass


def check_llm_rate_limit(user_id: str | None) -> None:
    settings = get_settings()
    if not settings.llm_rate_limit_enabled:
        return
    key_user = user_id or "anonymous"
    now_ms = int(time.time() * 1000)
    window_ms = 60_000
    key = f"rate_limit:llm:{key_user}"
    try:
        pipe = redis_conn.pipeline()
        pipe.zremrangebyscore(key, 0, now_ms - window_ms)
        pipe.zadd(key, {str(now_ms): now_ms})
        pipe.zcard(key)
        pipe.expire(key, 120)
        _, _, count, _ = pipe.execute()
    except Exception:
        return
    if int(count) > settings.llm_rate_limit_per_minute:
        raise RateLimitError(f"LLM rate limit exceeded: {settings.llm_rate_limit_per_minute} calls per minute")
