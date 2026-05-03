"""
Generic OpenAI-compatible adapter.

Use this for:
  * Local Ollama runs (point base_url at http://localhost:11434/v1)
  * Self-hosted vLLM
  * Any other endpoint that speaks the OpenAI chat-completions schema

This is also how this toolkit talks to ``sovereign-llm-quickstart`` —
the audit service there exposes /api/generate (Ollama-shape) and the
front of nginx exposes /v1/chat/completions if you wire it up.
"""

from __future__ import annotations

import time

import httpx

from adapters.base import Adapter, AdapterError, AdapterResponse


class GenericOpenAICompatAdapter(Adapter):
    name = "generic"

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str = "no-key-required",
        max_tokens: int = 600,
        timeout_s: float = 60.0,
        verify_tls: bool = True,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not base_url:
            raise AdapterError("generic adapter requires base_url")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.max_tokens = max_tokens
        self.timeout_s = timeout_s
        self.verify_tls = verify_tls
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
        }
        url = f"{self.base_url}/chat/completions"

        started = time.monotonic()
        try:
            client = self._client
            if client is None:
                async with httpx.AsyncClient(
                    timeout=self.timeout_s, verify=self.verify_tls,
                ) as c:
                    r = await c.post(url, headers=headers, json=body)
            else:
                r = await client.post(url, headers=headers, json=body)
        except httpx.HTTPError as exc:
            raise AdapterError(f"generic transport: {exc!r}") from exc
        latency_ms = int((time.monotonic() - started) * 1000)

        if r.status_code != 200:
            raise AdapterError(f"generic HTTP {r.status_code}")
        try:
            data = r.json()
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, ValueError) as exc:
            raise AdapterError(f"generic parse error: {exc!r}") from exc

        return AdapterResponse(
            text=text or "",
            latency_ms=latency_ms,
            model_reported=data.get("model", model),
        )
