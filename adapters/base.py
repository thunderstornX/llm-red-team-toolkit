"""
Adapter base class + shared types.

Adapters are async by design — the evaluator can run multiple probes
concurrently against API providers that allow it. We don't expose
streaming because the scorer needs the full response to classify it.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass


class AdapterError(Exception):
    """Raised by an adapter when transport or remote-side failure
    prevents a clean response. The harness treats this as outcome=error."""


@dataclass
class AdapterResponse:
    text: str
    latency_ms: int
    model_reported: str = ""   # what the *server* says it served


class Adapter(abc.ABC):
    """Abstract interface every adapter implements.

    Implementations should:
      * cap ``max_tokens`` server-side to a small number (we set 600)
        so DoS-style probes don't run up bills.
      * set ``temperature=0`` so the same probe + same model gives the
        same response across runs.
    """
    name: str = "abstract"

    @abc.abstractmethod
    async def generate(self, model: str, prompt: str) -> AdapterResponse:
        """Send ``prompt`` to ``model`` and return the response."""
