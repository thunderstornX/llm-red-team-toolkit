"""
NVIDIA NIM adapter.

NVIDIA serves models behind an OpenAI-compatible API at
``https://integrate.api.nvidia.com/v1/chat/completions`` (browse the
catalogue at build.nvidia.com). The API key starts with ``nvapi-`` and
is read from ``NVIDIA_API_KEY``.

The wire format is essentially identical to OpenRouter, but NVIDIA
sometimes nests the response payload differently for newer models, so
the parsing is slightly more defensive.
"""

from __future__ import annotations

import os
import time

import httpx

from adapters.base import Adapter, AdapterError, AdapterResponse


_DEFAULT_BASE_URL = "https://integrate.api.nvidia.com/v1"


class NvidiaNimAdapter(Adapter):
    name = "nvidia"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str = _DEFAULT_BASE_URL,
        max_tokens: int = 600,
        timeout_s: float = 60.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.api_key = api_key or os.environ.get("NVIDIA_API_KEY", "")
        if not self.api_key:
            raise AdapterError("NVIDIA_API_KEY not set.")
        self.base_url = base_url.rstrip("/")
        self.max_tokens = max_tokens
        self.timeout_s = timeout_s
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
            "Accept": "application/json",
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
            raise AdapterError(f"nvidia transport: {exc!r}") from exc
        latency_ms = int((time.monotonic() - started) * 1000)

        if r.status_code != 200:
            raise AdapterError(
                f"nvidia HTTP {r.status_code} for model={model}"
            )
        try:
            data = r.json()
            choices = data.get("choices") or []
            if not choices:
                raise AdapterError("nvidia: no choices in response")
            msg = choices[0].get("message") or {}
            text = msg.get("content")
            if text is None:
                # Some NIM models return the content split into chunks
                # even when stream=false. Reassemble defensively.
                parts = msg.get("content_parts") or []
                text = "".join(p.get("text", "") for p in parts)
            served = data.get("model", "")
        except (AttributeError, ValueError) as exc:
            raise AdapterError(f"nvidia parse error: {exc!r}") from exc

        return AdapterResponse(
            text=text or "",
            latency_ms=latency_ms,
            model_reported=served,
        )
