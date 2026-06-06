#!/usr/bin/env python3
"""
Render the TUI to PNG so the paper has real screenshots.

Each figure is a *recorded* Rich Console session: we capture the ANSI
output and rasterise it to PNG via a locally-installed monospace font
(see ``_export``). Driving the PNG directly from the ANSI capture is
more reproducible offline than the old SVG-with-webfont path, which
needed a font cache we can't assume is present.

Outputs (relative to repo root):

    paper/figures/banner.png
    paper/figures/dashboard.png
    paper/figures/summary.png
    paper/figures/list.png
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table

# Make package imports resolve when this script is run from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from probes.registry import filter_probes              # noqa: E402
from tui.banner import render_banner                   # noqa: E402
from tui.dashboard import Dashboard, DashboardState    # noqa: E402
from tui.report import render_summary                  # noqa: E402
from tui.theme import THEME                            # noqa: E402

import probes  # noqa: F401, E402  -- side-effect: register all probes


REPO_ROOT = Path(__file__).resolve().parent.parent
FIG_DIR = REPO_ROOT / "paper" / "figures"


def _new_console(width: int = 100) -> Console:
    """A recording Console with the toolkit theme installed."""
    return Console(
        record=True,
        width=width,
        force_terminal=True,
        color_system="256",
        theme=THEME,
        legacy_windows=False,
    )


def _export(c: Console, name: str, title: str) -> None:
    """Capture the recorded console output, then rasterise via PIL using
    a locally-installed monospace font. SVG-with-webfont was unreliable
    when the offline rasteriser had no font cache, so we drive the PNG
    directly from the ANSI capture instead."""
    from scripts.render_terminal import render as png_render
    png_path = FIG_DIR / f"{name}.png"
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    ansi = c.export_text(styles=True)
    png_render(ansi, png_path, font_size=15)
    print(f"  wrote {png_path.relative_to(REPO_ROOT)}")


def fig_banner() -> None:
    c = _new_console(width=82)
    render_banner(target_console=c)
    _export(c, "banner", "rtt :: banner")


def fig_list() -> None:
    c = _new_console(width=110)
    probes_subset = filter_probes(categories={"LLM01", "JAIL"})
    t = Table(title="probes (filtered: LLM01, JAIL)",
              border_style="rtt.border", show_lines=False, padding=(0, 1))
    t.add_column("id", style="rtt.muted")
    t.add_column("cat")
    t.add_column("severity")
    t.add_column("title")
    for p in probes_subset:
        cat_style = (f"rtt.cat.{p.category.lower()}"
                     if p.category != "JAIL" else "rtt.cat.jail")
        t.add_row(
            p.id,
            f"[{cat_style}]{p.category}[/]",
            f"[rtt.sev.{p.severity.value}]{p.severity.value.upper()}[/]",
            p.title,
        )
    c.print(t)
    _export(c, "list", "rtt :: list")


def fig_dashboard() -> None:
    """Replay the live dashboard against the real sample_report.json so
    the figure shows real probe outcomes."""
    sample = REPO_ROOT / "results" / "sample_report.json"
    data = json.loads(sample.read_text(encoding="utf-8"))
    rows = data["results"]
    state = DashboardState(
        target=data["run"]["adapter"],
        model=data["run"]["model"],
        total=len(rows),
    )
    # Replay the first 12 probes so the activity panel is full.
    for r in rows[:12]:
        state.record(r["id"], r["category"], r["outcome"])
    state.completed = 12
    state.total = len(rows)
    c = _new_console(width=110)
    dash = Dashboard(state, console=c)
    c.print(dash._layout())
    _export(c, "dashboard", "rtt :: live dashboard")


def fig_summary() -> None:
    sample = REPO_ROOT / "results" / "sample_report.json"
    data = json.loads(sample.read_text(encoding="utf-8"))
    counts = data["summary"]["by_outcome"]
    counts_full = {k: counts.get(k, 0)
                   for k in ("refused", "leaked", "partial", "skipped", "error")}
    c = _new_console(width=82)
    render_summary(
        target=data["run"]["adapter"],
        model=data["run"]["model"],
        counts=counts_full,
        elapsed_s=float(data["run"]["elapsed_s"]),
        console=c,
    )
    _export(c, "summary", "rtt :: scan summary")


def main() -> None:
    print("rendering figures into paper/figures/ ...")
    fig_banner()
    fig_list()
    fig_dashboard()
    fig_summary()
    print("done.")


if __name__ == "__main__":
    main()
