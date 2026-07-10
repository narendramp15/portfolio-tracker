"""Shared Anthropic Messages API client.

Single call path used by both the Options Analyzer proxy (``routers.ai_proxy``)
and the screener AI-thesis endpoint (``routers.stock_screener``) so timeouts,
error mapping, prompt-caching headers and content extraction stay identical.
"""

import logging

import httpx
from fastapi import HTTPException

logger = logging.getLogger(__name__)

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
ANTHROPIC_CACHING_BETA = "prompt-caching-2024-07-31"


async def call_anthropic(
    *,
    api_key: str,
    model: str,
    system_text: str,
    user_msg: str,
    max_tokens: int,
    timeout: float = 60.0,
) -> tuple[str, dict]:
    """Call the Anthropic Messages API and return ``(text, usage)``.

    ``system_text`` is sent with an ephemeral cache_control block. Non-2xx,
    timeout and network errors are mapped to the same HTTP statuses both
    callers previously used (502 / 504 / 502).
    """
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "system": [{"type": "text", "text": system_text, "cache_control": {"type": "ephemeral"}}],
        "messages": [{"role": "user", "content": user_msg}],
    }
    headers = {
        "x-api-key": api_key,
        "anthropic-version": ANTHROPIC_VERSION,
        "content-type": "application/json",
        "anthropic-beta": ANTHROPIC_CACHING_BETA,
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(ANTHROPIC_API_URL, json=payload, headers=headers)
        data = response.json()
        if response.status_code != 200:
            error_msg = data.get("error", {}).get("message", "Unknown error")
            logger.error("Anthropic API error %s: %s", response.status_code, error_msg)
            raise HTTPException(status_code=502, detail="AI service error. Please try again.")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Analysis timed out. Please try again.")
    except httpx.RequestError as exc:
        logger.exception("Network error calling AI service: %s", exc)
        raise HTTPException(status_code=502, detail="Network error. Please try again.")

    text = "".join(
        block.get("text", "") for block in data.get("content", [])
        if isinstance(block, dict)
    )
    return text, data.get("usage", {})
