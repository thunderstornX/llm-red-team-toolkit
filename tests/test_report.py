"""
Report writer round-trip tests.

We construct a fake set of results, write JSON + Markdown, and assert
the contents are well-formed. The Markdown writer is asserted on
shape, not on exact wording — paper text isn't load-bearing for tests.
"""

from __future__ import annotations

import json
from pathlib import Path

from harness.config import RunOptions, TargetConfig
from harness.report import write_json_report, write_markdown_report
from probes.base import ProbeResult


def _make_results() -> list[ProbeResult]:
    return [
        ProbeResult(
            probe_id="llm01.x", category="LLM01", severity="high",
            payload_sent="p", response="I cannot help.", outcome="refused",
            confidence=0.9, notes="generic refusal",
        ),
        ProbeResult(
            probe_id="llm06.y", category="LLM06", severity="med",
            payload_sent="p", response="here is the secret",
            outcome="leaked", confidence=0.8, notes="success marker hit",
        ),
        ProbeResult(
            probe_id="jail.z", category="JAIL", severity="high",
            payload_sent="p", response="...", outcome="partial",
            confidence=0.3, notes="ambiguous",
        ),
    ]


def _target() -> TargetConfig:
    return TargetConfig(adapter="openrouter", model="vendor/m")


def _opts() -> RunOptions:
    return RunOptions()


def test_json_report_is_valid(tmp_path: Path):
    out = tmp_path / "report.json"
    write_json_report(_target(), _opts(), _make_results(), elapsed_s=1.5,
                      out_path=out)
    doc = json.loads(out.read_text())
    assert doc["schema_version"] == 1
    assert doc["tool"] == "llm-red-team-toolkit"
    assert doc["summary"]["total"] == 3
    by_outcome = doc["summary"]["by_outcome"]
    assert by_outcome.get("refused") == 1
    assert by_outcome.get("leaked") == 1
    assert by_outcome.get("partial") == 1
    by_cat = doc["summary"]["by_category"]
    assert by_cat["LLM01"]["refused"] == 1
    assert by_cat["LLM06"]["leaked"] == 1
    assert by_cat["JAIL"]["partial"] == 1
    assert len(doc["results"]) == 3
    # The probe_id alias rename:
    assert "id" in doc["results"][0]
    assert "probe_id" not in doc["results"][0]


def test_markdown_report_has_expected_sections(tmp_path: Path):
    out = tmp_path / "report.md"
    write_markdown_report(_target(), _opts(), _make_results(), elapsed_s=2.0,
                          out_path=out)
    md = out.read_text()
    assert "# Red-team scan report" in md
    assert "## Outcome breakdown" in md
    assert "## By OWASP category" in md
    assert "## Per-probe details" in md
    assert "vendor/m" in md
    # All three categories represented:
    assert "LLM01" in md and "LLM06" in md and "JAIL" in md
    # Markdown table headers present:
    assert "| outcome | count | % |" in md


def test_markdown_escapes_pipes_in_notes(tmp_path: Path):
    rs = [ProbeResult(
        probe_id="x.y", category="LLM01", severity="med",
        payload_sent="p", response="r", outcome="partial", confidence=0.5,
        notes="note has | a pipe in it",
    )]
    out = tmp_path / "report.md"
    write_markdown_report(_target(), _opts(), rs, 1.0, out)
    md = out.read_text()
    assert r"note has \| a pipe in it" in md
