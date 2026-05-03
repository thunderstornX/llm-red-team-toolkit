"""
Target adapters: send a prompt to a thing, get a response back.

Each adapter is responsible for the *transport*, not the *meaning*. It
takes a string prompt, hits an HTTP endpoint, and returns a string
response with a latency measurement. Errors propagate as
``AdapterError`` — the harness decides whether to mark the probe as
"error" or to retry.
"""

from adapters.base import Adapter, AdapterError, AdapterResponse
from adapters.generic import GenericOpenAICompatAdapter
from adapters.nvidia import NvidiaNimAdapter
from adapters.openrouter import OpenRouterAdapter

__all__ = [
    "Adapter",
    "AdapterError",
    "AdapterResponse",
    "GenericOpenAICompatAdapter",
    "NvidiaNimAdapter",
    "OpenRouterAdapter",
]
