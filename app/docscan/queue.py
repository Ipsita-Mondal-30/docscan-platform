"""Tiny queue abstraction: Redis in production, in-memory in tests."""
import queue as _q

import redis

from .config import settings


class RedisQueue:
    def __init__(self, url: str | None = None, name: str | None = None):
        # socket timeout must exceed the BLPOP block time, or idle workers die with TimeoutError
        self.r = redis.Redis.from_url(url or settings.redis_url, socket_timeout=30, socket_connect_timeout=5)
        self.name = name or settings.queue_name

    def push(self, job_id: str) -> None:
        self.r.rpush(self.name, job_id)

    def pop(self, timeout: int = 5) -> str | None:
        item = self.r.blpop(self.name, timeout=timeout)
        return item[1].decode() if item else None

    def depth(self) -> int:
        return int(self.r.llen(self.name))

    def ping(self) -> bool:
        return bool(self.r.ping())


class MemoryQueue:
    def __init__(self):
        self._q: _q.Queue = _q.Queue()

    def push(self, job_id: str) -> None:
        self._q.put(job_id)

    def pop(self, timeout: int = 1) -> str | None:
        try:
            return self._q.get(timeout=timeout)
        except _q.Empty:
            return None

    def depth(self) -> int:
        return self._q.qsize()

    def ping(self) -> bool:
        return True
