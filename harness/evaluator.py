"""
Evaluator: run probes against a target, return results.

This is a pure-async dispatcher. It does *not* know about the TUI; the
caller (``cli.py``) pipes results into the dashboard. That separation
is on purpose — the eval can be driven from a notebook, a unit test,
or a CI script without dragging Rich into the dependency graph at
import time.
"""

from __future__ import annotations

import asyncio
import time
from typing import AsyncIterator, Callable, Optional

from adapters.base import Adapter, AdapterError
from harness.config import RunOptions
from harness.scorer import score
from probes.base import Probe, ProbeResult


# Hook signature for the live dashboard callback. Kept as Callable so
# the harness has zero rich/terminal imports.
ProgressCb = Callable[[ProbeResult], None]


class Evaluator:
    """Runs an iterable of probes through an adapter, with a small
    concurrency pool. Yields ``ProbeResult`` objects in completion
    order — *not* in submission order — so a slow LLM doesn't stall a
    fast cohort."""

    def __init__(
        self,
        adapter: Adapter,
        model: str,
        opts: RunOptions,
    ) -> None:
        self.adapter = adapter
        self.model = model
        self.opts = opts

    async def _one(self, probe: Probe) -> ProbeResult:
        if self.opts.dry_run:
            # Don't hit the network, but pretend the model gave us back
            # the same canary the probe was looking for. Useful for
            # exercising the report writers in CI.
            fake = " ".join(probe.success_markers[:1]) or "(dry-run response)"
            return score(probe, fake, latency_ms=0)
        try:
            resp = await self.adapter.generate(self.model, probe.payload)
        except AdapterError as exc:
            return ProbeResult.errored(probe, error=str(exc))

        result = score(probe, resp.text, latency_ms=resp.latency_ms)
        if not self.opts.record_responses:
            # Redact the raw response on its way out, but keep enough
            # for after-the-fact triage (first 200 chars + length).
            head = result.response[:200]
            tail_len = max(0, len(result.response) - 200)
            result.response = head + (f"... [+{tail_len} chars redacted]"
                                      if tail_len else "")
        return result

    async def run(
        self,
        probes: list[Probe],
        on_result: Optional[ProgressCb] = None,
    ) -> AsyncIterator[ProbeResult]:
        """Async generator yielding results as they finish."""
        sem = asyncio.Semaphore(self.opts.concurrency)

        async def _wrapped(p: Probe) -> ProbeResult:
            async with sem:
                return await self._one(p)

        # Submit all up front. asyncio.as_completed yields futures in
        # finish order, which is what we want for the live dashboard.
        tasks = [asyncio.create_task(_wrapped(p)) for p in probes]
        try:
            for coro in asyncio.as_completed(tasks):
                result = await coro
                if on_result is not None:
                    on_result(result)
                yield result
        finally:
            # If the caller stops iterating early, cancel outstanding
            # network calls so they don't get billed.
            for t in tasks:
                if not t.done():
                    t.cancel()


async def run_to_list(
    adapter: Adapter,
    model: str,
    probes: list[Probe],
    opts: RunOptions,
    on_result: Optional[ProgressCb] = None,
) -> tuple[list[ProbeResult], float]:
    """Convenience: run, drain into a list, return (results, elapsed_s)."""
    started = time.monotonic()
    ev = Evaluator(adapter, model, opts)
    results: list[ProbeResult] = []
    async for r in ev.run(probes, on_result=on_result):
        results.append(r)
    return results, time.monotonic() - started
