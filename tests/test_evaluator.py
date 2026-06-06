"""
Evaluator dispatch tests.

Uses the shared ``fake_adapter`` fixture (no network) so we can drive
deterministic responses through the scoring pipeline and verify the
evaluator yields one result per probe, respects concurrency, and handles
dry-run + the error path.
"""

from __future__ import annotations

import pytest

from harness.config import RunOptions
from harness.evaluator import run_to_list
from probes.registry import filter_probes


@pytest.mark.asyncio
async def test_dry_run_makes_no_network_calls(fake_adapter):
    probes = filter_probes(categories={"LLM01"})
    fake = fake_adapter(responses={})
    opts = RunOptions(dry_run=True, concurrency=1)
    results, _ = await run_to_list(fake, "fake/m", probes, opts)
    assert fake.call_count == 0
    assert len(results) == len(probes)
    # LLM01 probes all carry success markers; dry-run echoes the first,
    # so every result is "leaked".
    assert all(r.outcome == "leaked" for r in results)


@pytest.mark.asyncio
async def test_real_dispatch_returns_one_result_per_probe(fake_adapter):
    probes = filter_probes(categories={"LLM01"})
    canned = {p.payload: "I cannot do that." for p in probes}
    fake = fake_adapter(responses=canned)
    opts = RunOptions(dry_run=False, concurrency=2)
    results, _ = await run_to_list(fake, "fake/m", probes, opts)
    assert len(results) == len(probes)
    assert fake.call_count == len(probes)
    assert all(r.outcome == "refused" for r in results)


@pytest.mark.asyncio
async def test_adapter_error_becomes_error_outcome(fake_adapter):
    probes = filter_probes(categories={"LLM01"})[:2]
    fake = fake_adapter(
        responses={p.payload: "ok" for p in probes},
        raise_on={p.payload for p in probes},
    )
    opts = RunOptions(dry_run=False, concurrency=1)
    results, _ = await run_to_list(fake, "fake/m", probes, opts)
    assert all(r.outcome == "error" for r in results)
    assert all(r.error and "transport" in r.error for r in results)


@pytest.mark.asyncio
async def test_no_record_responses_truncates(fake_adapter):
    probes = filter_probes(categories={"LLM01"})[:1]
    long = "X" * 1000
    canned = {probes[0].payload: long}
    fake = fake_adapter(responses=canned)
    opts = RunOptions(dry_run=False, concurrency=1, record_responses=False)
    results, _ = await run_to_list(fake, "fake/m", probes, opts)
    # First 200 of X plus a redaction marker.
    assert results[0].response.startswith("X" * 200)
    assert "redacted" in results[0].response


@pytest.mark.asyncio
async def test_concurrency_runs_in_parallel(fake_adapter):
    """If concurrency=N > 1, total wall-time should be << sum-of-delays."""
    probes = filter_probes(categories={"LLM01"})  # 5 probes
    canned = {p.payload: "I won't." for p in probes}
    fake = fake_adapter(responses=canned, delay_s=0.05)

    opts = RunOptions(dry_run=False, concurrency=5)
    results, elapsed = await run_to_list(fake, "fake/m", probes, opts)

    # Serial would take >= 5 * 0.05 = 0.25s. Parallel should be ~0.05s.
    # Allow generous slack for CI.
    assert elapsed < 0.20, f"parallel run too slow: {elapsed:.3f}s"
    assert len(results) == len(probes)
