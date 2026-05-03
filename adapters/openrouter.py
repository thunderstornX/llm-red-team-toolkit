"""
OpenRouter adapter.

OpenRouter exposes an OpenAI-compatible chat-completions endpoint at
``https://openrouter.ai/api/v1/chat/completions``. One API key gives
you access to a hundred-ish models. We use a single chat turn — no
streaming, no system prompt unless the probe carries one.

API key is read from the ``OPENROUTER_API_KEY`` env var. The adapter
never logs the key, never includes it in error messages, never writes
it to disk.
"""

from __future__ import annotations

import os
import time

import httpx

from adapters.base import Adapter, AdapterError, AdapterResponse


_DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"


class OpenRouterAdapter(Adapter):
    name = "openrouter"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str = _DEFAULT_BASE_URL,
        max_tokens: int = 600,
        timeout_s: float = 60.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
        if not self.api_key:
            raise AdapterError(
                "OPENROUTER_API_KEY not set. Either pass api_key= or "
                "export the env var. (We never read keys from files.)"
            )
        self.base_url = base_url.rstrip("/")
        self.max_tokens = max_tokens
        self.timeout_s = timeout_s
        # Caller-injected client lets tests pass an httpx.AsyncClient
        # backed by respx without us punching a hole in the abstraction.
        self._client = client

    async def generate(self, model: str, prompt: str) -> AdapterResponse:
        body = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "max_tokens": self.max_tokens,
            "stream": False,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            # OpenRouter politely asks for these so they can show
            # attribution on their dashboard. Defensive testing tool;
            # we tell them so.
            "HTTP-Referer": "https://github.com/thunderstornX/llm-red-team-toolkit",
            "X-Title": "llm-red-team-toolkit",
        }
        url = f"{self.base_url}/chat/completions"

        started = time.monotonic()
        try:
            client = self._client
            if client is None:
                async with httpx.AsyncClient(timeout=self.timeout_s) as c:
                    r = await c.post(url, headers=headers, json=body)
            else:
                r = await client.post(url, headers=headers, json=body)
        except httpx.HTTPError as exc:
            raise AdapterError(f"openrouter transport: {exc!r}") from exc
        latency_ms = int((time.monotonic() - started) * 1000)

        if r.status_code != 200:
            # Don't echo response body — providers occasionally include
            # a hint of the inbound request in their error JSON.
            raise AdapterError(
                f"openrouter HTTP {r.status_code} for model={model}"
            )
        try:
            data = r.json()
            text = data["choices"][0]["message"]["content"]
            served = data.get("model", "")
        except (KeyError, IndexError, ValueError) as exc:
            raise AdapterError(f"openrouter parse error: {exc!r}") from exc

        return AdapterResponse(
            text=text or "",
            latency_ms=latency_ms,
            model_reported=served,
        )
