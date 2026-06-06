"""
Report writers: JSON for machines, Markdown for humans.

The JSON file is the canonical artefact — every other view is derived
from it. We never re-derive metrics inside the Markdown writer; the
machine-readable file is the source of truth, and Markdown just
renders it.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from harness.config import RunOptions, TargetConfig
from probes.base import ProbeResult
from tui.report import CATEGORY_LABELS


def _utc_iso(dt: datetime | None = None) -> str:
    return (dt or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_json_report(
    target: TargetConfig,
    opts: RunOptions,
    results: list[ProbeResult],
    elapsed_s: float,
    out_path: Path,
    *,
    started_at: datetime | None = None,
) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    counts = Counter(r.outcome for r in results)
    cat_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in results:
        cat_counts[r.category][r.outcome] += 1
        cat_counts[r.category]["total"] += 1

    doc = {
        "schema_version": 1,
        "tool": "llm-red-team-toolkit",
        "tool_version": "1.0.0",
        "run": {
            "started_utc": _utc_iso(started_at),
            "elapsed_s": round(elapsed_s, 2),
            "adapter": target.adapter,
            "model": target.model,
            "concurrency": opts.concurrency,
            "dry_run": opts.dry_run,
            "record_responses": opts.record_responses,
            "filters": {
                "categories": list(opts.categories),
                "tags": list(opts.tags),
            },
        },
        "summary": {
            "total": len(results),
            "by_outcome": dict(counts),
            "by_category": {k: dict(v) for k, v in cat_counts.items()},
        },
        "results": [r.to_dict() for r in results],
    }
    out_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False),
                        encoding="utf-8")
    return out_path


def write_markdown_report(
    target: TargetConfig,
    opts: RunOptions,
    results: list[ProbeResult],
    elapsed_s: float,
    out_path: Path,
    *,
    started_at: datetime | None = None,
) -> Path:
    """Write a Markdown summary suitable for a Pull Request comment or
    a paper appendix. Self-contained — does not depend on the JSON
    file."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    counts = Counter(r.outcome for r in results)
    total = len(results) or 1

    lines: list[str] = []
    lines.append(f"# Red-team scan report")
    lines.append("")
    lines.append(f"- **target**: `{target.adapter}` :: `{target.model}`")
    lines.append(f"- **scanned at**: {_utc_iso(started_at)}")
    lines.append(f"- **probes run**: {len(results)}")
    lines.append(f"- **wall-clock**: {elapsed_s:.1f}s "
                 f"(concurrency = {opts.concurrency})")
    if opts.dry_run:
        lines.append("- **dry-run**: yes — no network calls were made")
    lines.append("")

    lines.append("## Outcome breakdown")
    lines.append("")
    lines.append("| outcome | count | % |")
    lines.append("|---|---:|---:|")
    for k in ("refused", "leaked", "partial", "skipped", "error"):
        n = counts.get(k, 0)
        pct = 100 * n / total
        lines.append(f"| **{k}** | {n} | {pct:.1f} % |")
    lines.append("")

    lines.append("## By OWASP category")
    lines.append("")
    lines.append("| category | total | refused | leaked | partial | skipped | error |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    by_cat: dict[str, Counter] = defaultdict(Counter)
    for r in results:
        by_cat[r.category][r.outcome] += 1
    for cat in sorted(by_cat):
        cc = by_cat[cat]
        label = CATEGORY_LABELS.get(cat, cat)
        lines.append(
            f"| **{cat}** {label} | {sum(cc.values())} | "
            f"{cc.get('refused', 0)} | {cc.get('leaked', 0)} | "
            f"{cc.get('partial', 0)} | {cc.get('skipped', 0)} | "
            f"{cc.get('error', 0)} |"
        )
    lines.append("")

    lines.append("## Per-probe details")
    lines.append("")
    grouped: dict[str, list[ProbeResult]] = defaultdict(list)
    for r in results:
        grouped[r.category].append(r)
    for cat in sorted(grouped):
        label = CATEGORY_LABELS.get(cat, cat)
        lines.append(f"### {cat} — {label}")
        lines.append("")
        lines.append("| probe | severity | outcome | confidence | notes |")
        lines.append("|---|---|---|---:|---|")
        for r in grouped[cat]:
            notes = (r.notes or "").replace("|", r"\|")
            lines.append(
                f"| `{r.probe_id}` | {r.severity} | **{r.outcome}** | "
                f"{r.confidence:.2f} | {notes} |"
            )
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("Report generated by `llm-red-team-toolkit` v1.0.0. ")
    lines.append("This run is a *vulnerability scan*, not an exploit; ")
    lines.append("findings should be triaged against your deployment ")
    lines.append("context. See `ETHICAL_USE.md`.")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path
