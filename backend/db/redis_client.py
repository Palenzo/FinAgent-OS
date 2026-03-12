"""
Redis client — shared cache layer for agent outputs.
Cache TTL: 1 hour by default (cost-controls for Claude API).
"""

import json
import os
from typing import Any, Optional

import redis.asyncio as aioredis

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
DEFAULT_TTL = 3600  # 1 hour

_pool: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    global _pool
    if _pool is None:
        _pool = await aioredis.from_url(REDIS_URL, decode_responses=True)
    return _pool


async def cache_set(key: str, value: Any, ttl: int = DEFAULT_TTL):
    r = await get_redis()
    await r.set(key, json.dumps(value), ex=ttl)


async def cache_get(key: str) -> Optional[Any]:
    r = await get_redis()
    raw = await r.get(key)
    if raw is None:
        return None
    return json.loads(raw)


async def cache_delete(key: str):
    r = await get_redis()
    await r.delete(key)


async def publish_event(channel: str, event: dict):
    """Publish real-time events to Redis pub/sub (picked up by Dashboard Agent)."""
    r = await get_redis()
    await r.publish(channel, json.dumps(event))
