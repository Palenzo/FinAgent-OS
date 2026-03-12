"""
Claude API wrapper used by all agents.
Caches identical (system_prompt, context) pairs in Redis for 1 hour.
"""

import hashlib
import json
import os
import time
from typing import Optional

import anthropic

from db.redis_client import cache_get, cache_set

_client: Optional[anthropic.Anthropic] = None

SONNET = "claude-sonnet-4-6"
OPUS = "claude-opus-4-6"


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _client


def _hash_key(system_prompt: str, context: dict) -> str:
    raw = system_prompt + json.dumps(context, sort_keys=True)
    return "claude:" + hashlib.sha256(raw.encode()).hexdigest()


async def run_agent(
    system_prompt: str,
    context: dict,
    model: str = SONNET,
    max_tokens: int = 2048,
    tools: Optional[list] = None,
    use_cache: bool = True,
) -> dict:
    """
    Call Claude and return:
    {
        "text": str,
        "tokens_used": int,
        "model": str,
        "cached": bool,
    }
    """
    cache_key = _hash_key(system_prompt, context)

    if use_cache:
        cached = await cache_get(cache_key)
        if cached:
            cached["cached"] = True
            return cached

    client = get_client()
    kwargs = dict(
        model=model,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": f"Financial context:\n{json.dumps(context, indent=2)}",
            }
        ],
    )
    if tools:
        kwargs["tools"] = tools

    t0 = time.monotonic()
    response = client.messages.create(**kwargs)
    elapsed_ms = int((time.monotonic() - t0) * 1000)

    text = ""
    for block in response.content:
        if hasattr(block, "text"):
            text += block.text

    result = {
        "text": text,
        "tokens_used": response.usage.input_tokens + response.usage.output_tokens,
        "model": model,
        "cached": False,
        "duration_ms": elapsed_ms,
    }

    if use_cache:
        await cache_set(cache_key, result)

    return result
