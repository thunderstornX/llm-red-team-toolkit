"""
Adapter wire-format tests using respx.

We don't hit the real network. Every test mounts a respx mock for the
upstream URL, feeds in a canonical OpenAI-shaped chat-completions
JSON, and asserts the adapter parses it cleanly.
"""

from __future__ import annotations

import asyncio

import httpx
import pytest
import respx

from adapters.base import AdapterError
from adapters.generic import GenericOpenAICompatAdapter
from adapters.nvidia import NvidiaNimAdapter
from adapters.openrouter import OpenRouterAdapter


_OK_BODY = {
    "id": "chatcmpl-x",
    "model": "test/model:1",
    "choices": [
        {
            "index": 0,
            "message": {"role": "assistant", "content": "hello back"},
            "finish_reason": "stop",
        }
    ],
}


@pytest.mark.asyncio
async def test_openrouter_happy_path():
    async with respx.mock(assert_all_called=True, base_url="https://openrouter.ai") as mock:
        mock.post("/api/v1/chat/completions").mock(
            return_value=httpx.Response(200, json=_OK_BODY),
        )
        async with httpx.AsyncClient() as c:
            ad = OpenRouterAdapter(api_key="sk-or-test", client=c)
            r = await ad.generate("test/model:1", "hi")
        assert r.text == "hello back"
        assert r.model_reported == "test/model:1"
        assert r.latency_ms >= 0


@pytest.mark.asyncio
async def test_openrouter_propagates_http_error():
    async with respx.mock(base_url="https://openrouter.ai") as mock:
        mock.post("/api/v1/chat/completions").mock(
            return_value=httpx.Response(429, json={"error": "rate_limited"}),
        )
        async with httpx.AsyncClient() as c:
            ad = OpenRouterAdapter(api_key="sk-or-test", client=c)
            with pytest.raises(AdapterError) as ei:
                await ad.generate("any/model", "hi")
        # Error message must NOT include the response body.
        assert "rate_limited" not in str(ei.value)
        assert "429" in str(ei.value)


@pytest.mark.asyncio
async def test_openrouter_requires_key():
    with pytest.raises(AdapterError):
        OpenRouterAdapter(api_key="")


@pytest.mark.asyncio
async def test_nvidia_happy_path():
    async with respx.mock(base_url="https://integrate.api.nvidia.com") as mock:
        mock.post("/v1/chat/completions").mock(
            return_value=httpx.Response(200, json=_OK_BODY),
        )
        async with httpx.AsyncClient() as c:
            ad = NvidiaNimAdapter(api_key="nvapi-test", client=c)
            r = await ad.generate("vendor/m", "hi")
        assert r.text == "hello back"


@pytest.mark.asyncio
async def test_nvidia_handles_missing_choices():
    async with respx.mock(base_url="https://integrate.api.nvidia.com") as mock:
        mock.post("/v1/chat/completions").mock(
            return_value=httpx.Response(200, json={"choices": []}),
        )
        async with httpx.AsyncClient() as c:
            ad = NvidiaNimAdapter(api_key="nvapi-test", client=c)
            with pytest.raises(AdapterError):
                await ad.generate("vendor/m", "hi")


@pytest.mark.asyncio
async def test_generic_adapter_calls_v1_chat_completions():
    async with respx.mock() as mock:
        route = mock.post("http://localhost:11434/v1/chat/completions").mock(
            return_value=httpx.Response(200, json=_OK_BODY),
        )
        async with httpx.AsyncClient() as c:
            ad = GenericOpenAICompatAdapter(
                base_url="http://localhost:11434/v1", client=c,
            )
            await ad.generate("llama3.2:1b", "hi")
        assert route.called


@pytest.mark.asyncio
async def test_adapters_never_log_api_key(capsys):
    """Whatever happens, the api key must never end up in stdout/stderr."""
    secret = "sk-or-LEAKAGE-CANARY-2026"
    async with respx.mock(base_url="https://openrouter.ai") as mock:
        mock.post("/api/v1/chat/completions").mock(
            return_value=httpx.Response(500, text="server error"),
        )
        async with httpx.AsyncClient() as c:
            ad = OpenRouterAdapter(api_key=secret, client=c)
            try:
                await ad.generate("any/m", "hi")
            except AdapterError:
                pass
    captured = capsys.readouterr()
    assert secret not in captured.out
    assert secret not in captured.err
