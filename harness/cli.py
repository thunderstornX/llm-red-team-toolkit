"""
CLI entry point.

Two commands:

    rtt list       -- show all registered probes (filterable)
    rtt scan       -- run probes against a target, render a TUI, write reports

We use Typer because it gives us free help text, type-coerced flags,
and clean subcommand routing without writing argparse boilerplate.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Optional

import typer

from adapters.base import Adapter, AdapterError
from adapters.generic import GenericOpenAICompatAdapter
from adapters.nvidia import NvidiaNimAdapter
from adapters.openrouter import OpenRouterAdapter
from harness.config import RunOptions, TargetConfig
from harness.evaluator import run_to_list
from harness.report import write_json_report, write_markdown_report
from probes import all_probes
from probes.registry import filter_probes
from tui.banner import render_banner, render_compact_banner
from tui.dashboard import Dashboard, DashboardState
from tui.report import render_summary, render_full
from tui.theme import console


app = typer.Typer(
    add_completion=False,
    help="rtt :: llm-red-team-toolkit. OWASP-aligned probing for LLM endpoints.",
    rich_markup_mode="rich",
    no_args_is_help=True,
)


def _build_adapter(target: TargetConfig) -> Adapter:
    if target.adapter == "openrouter":
        return OpenRouterAdapter(
            max_tokens=target.max_tokens, timeout_s=target.timeout_s,
        )
    if target.adapter == "nvidia":
        return NvidiaNimAdapter(
            max_tokens=target.max_tokens, timeout_s=target.timeout_s,
        )
    if target.adapter == "generic":
        if not target.base_url:
            raise typer.BadParameter(
                "generic adapter requires --base-url"
            )
        return GenericOpenAICompatAdapter(
            base_url=target.base_url,
            max_tokens=target.max_tokens,
            timeout_s=target.timeout_s,
            verify_tls=target.verify_tls,
        )
    raise typer.BadParameter(f"unknown adapter: {target.adapter!r}")


@app.command("list", help="Show all registered probes (with optional filters).")
def cmd_list(
    category: Optional[str] = typer.Option(
        None, "--category", "-c",
        help="Filter by OWASP code (LLM01..LLM10) or JAIL.",
    ),
    tag: Optional[str] = typer.Option(
        None, "--tag", "-t", help="Filter by tag (e.g. base64).",
    ),
    quiet: bool = typer.Option(False, "--quiet", "-q",
                               help="Compact one-liner banner."),
) -> None:
    if quiet:
        render_compact_banner()
    else:
        render_banner()

    cats = (category,) if category else ()
    tags = (tag,) if tag else ()
    probes = filter_probes(categories=cats or None, tags=tags or None)

    from rich.table import Table
    t = Table(title="probes", border_style="rtt.border",
              show_lines=False, padding=(0, 1))
    t.add_column("id", style="rtt.muted")
    t.add_column("cat")
    t.add_column("severity")
    t.add_column("title")
    t.add_column("tags", style="rtt.muted")
    for p in probes:
        cat_style = (f"rtt.cat.{p.category.lower()}"
                     if p.category != "JAIL" else "rtt.cat.jail")
        t.add_row(
            p.id,
            f"[{cat_style}]{p.category}[/]",
            f"[rtt.sev.{p.severity.value}]{p.severity.value.upper()}[/]",
            p.title,
            " ".join(p.tags),
        )
    console.print(t)
    console.print(f"\n[rtt.muted]{len(probes)} probe(s) shown.[/]")


@app.command("scan", help="Run probes against a target and write reports.")
def cmd_scan(
    adapter: str = typer.Option(
        "openrouter", "--adapter", "-a",
        help="Target adapter: openrouter / nvidia / generic.",
    ),
    model: str = typer.Option(
        "anthropic/claude-haiku-4-5", "--model", "-m",
        help="Model identifier passed to the adapter.",
    ),
    base_url: Optional[str] = typer.Option(
        None, "--base-url", help="Base URL for the generic adapter only.",
    ),
    category: Optional[str] = typer.Option(
        None, "--category", "-c",
        help="Run only probes in this OWASP category (LLM01..LLM10 or JAIL).",
    ),
    tag: Optional[str] = typer.Option(
        None, "--tag", "-t", help="Run only probes with this tag.",
    ),
    concurrency: int = typer.Option(
        4, "--concurrency", "-j", min=1, max=32,
        help="How many probes to run in parallel against the adapter.",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run",
        help="Score using a fake response; no network calls.",
    ),
    no_record_responses: bool = typer.Option(
        False, "--no-record-responses",
        help="Truncate raw responses on the way to disk.",
    ),
    output_dir: Path = typer.Option(
        Path("results/runs"), "--output-dir", "-o",
        help="Where to write the JSON + Markdown reports.",
    ),
    verify_tls: bool = typer.Option(
        True, "--verify-tls/--no-verify-tls",
        help="Validate the upstream TLS cert (off only for local self-signed).",
    ),
    quiet: bool = typer.Option(False, "--quiet", "-q",
                               help="Compact banner only."),
) -> None:
    if quiet:
        render_compact_banner()
    else:
        render_banner()

    target = TargetConfig(
        adapter=adapter, model=model, base_url=base_url,
        verify_tls=verify_tls,
    )
    opts = RunOptions(
        categories=(category,) if category else (),
        tags=(tag,) if tag else (),
        concurrency=concurrency,
        record_responses=not no_record_responses,
        output_dir=output_dir,
        dry_run=dry_run,
    )

    cats = opts.categories or None
    tag_set = opts.tags or None
    probes = filter_probes(categories=cats, tags=tag_set)
    if not probes:
        console.print("[rtt.error]no probes match the requested filters.[/]")
        raise typer.Exit(code=2)

    if opts.dry_run:
        # Dry-run skips network I/O entirely. We still need *something*
        # that quacks like an adapter so the evaluator type-checks; the
        # generic adapter accepts a dummy base_url and is never called.
        adapter_obj = GenericOpenAICompatAdapter(
            base_url="http://dry-run.local", api_key="not-used",
        )
    else:
        try:
            adapter_obj = _build_adapter(target)
        except AdapterError as exc:
            console.print(f"[rtt.error]adapter init failed: {exc}[/]")
            raise typer.Exit(code=3)

    state = DashboardState(
        target=target.adapter, model=target.model, total=len(probes),
    )
    dash = Dashboard(state)
    results = []

    async def _go():
        with dash.live() as live:
            def _on(result):
                state.record(result.probe_id, result.category, result.outcome)
                dash.render_into(live)

            r, elapsed = await run_to_list(
                adapter_obj, target.model, probes, opts, on_result=_on,
            )
            return r, elapsed

    results, elapsed = asyncio.run(_go())

    # Write artefacts.
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = target.model.replace("/", "_").replace(":", "_")
    json_path = output_dir / f"{target.adapter}_{stamp}.json"
    md_path = output_dir / f"{target.adapter}_{stamp}.md"
    write_json_report(target, opts, results, elapsed, json_path)
    write_markdown_report(target, opts, results, elapsed, md_path)

    console.print()
    render_summary(
        target=f"{target.adapter}",
        model=target.model,
        counts={k: 0 for k in ("refused", "leaked", "partial", "skipped", "error")} | {
            k: sum(1 for r in results if r.outcome == k)
            for k in ("refused", "leaked", "partial", "skipped", "error")
        },
        elapsed_s=elapsed,
    )
    console.print(
        f"[rtt.muted]reports written:[/]\n"
        f"  [rtt.muted]json:[/]     {json_path}\n"
        f"  [rtt.muted]markdown:[/] {md_path}"
    )


if __name__ == "__main__":  # pragma: no cover
    app()
