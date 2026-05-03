"""
Live probe-execution dashboard.

When the harness is running, the human looking at the screen wants to
know three things:

    1. how far through the run am i?
    2. what is the model doing right now?
    3. has anything caught fire yet?

This module renders all three in one Rich ``Live`` view: a top progress
bar for #1, a streaming activity log for #2, and a running scoreboard
for #3. All three update in place — no scroll-spam.

We deliberately do NOT use Rich's ``rich.live.Live`` with refresh thread
that fights asyncio. Instead the harness drives ``Dashboard.tick()``
explicitly between probe completions, which keeps the rendering on the
event loop and predictable in tests.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Iterable, Optional

from rich.console import Group, RenderableType
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table
from rich.text import Text

from tui.theme import console as _default_console

# Outcome labels match what scorer.py emits. Keep these in sync.
OUTCOMES = ("refused", "leaked", "partial", "skipped", "error")


@dataclass
class DashboardState:
    """Mutable state the dashboard renders. The harness owns this; the
    dashboard just looks at it."""
    target: str = "—"
    model: str = "—"
    total: int = 0
    completed: int = 0
    counts: Counter = field(default_factory=Counter)
    activity: list[str] = field(default_factory=list)  # most-recent-last
    activity_limit: int = 10
    started_at: float = 0.0

    def record(self, probe_id: str, category: str, outcome: str) -> None:
        self.completed += 1
        self.counts[outcome] += 1
        marker = {
            "refused": "[rtt.refused]REFUSED[/]",
            "leaked":  "[rtt.leaked]LEAKED [/]",
            "partial": "[rtt.partial]PARTIAL[/]",
            "skipped": "[rtt.skipped]SKIPPED[/]",
            "error":   "[rtt.error]ERROR  [/]",
        }.get(outcome, "[rtt.muted]?      [/]")
        line = f"{marker}  [rtt.muted]{category:<8}[/] {probe_id}"
        self.activity.append(line)
        # keep only the tail
        del self.activity[: max(0, len(self.activity) - self.activity_limit)]


class Dashboard:
    """Renders ``DashboardState`` as a Rich Live view.

    Usage::

        dash = Dashboard(state)
        with dash.live() as live:
            for probe in probes:
                ...   # run probe
                state.record(probe.id, probe.category, outcome)
                live.refresh()
    """

    def __init__(
        self,
        state: DashboardState,
        console=None,
        title: str = "rtt :: live scan",
    ) -> None:
        self.state = state
        self.console = console or _default_console
        self.title = title
        self._progress: Optional[Progress] = None
        self._task_id = None

    # ------- renderables ------------------------------------------------

    def _scoreboard(self) -> Table:
        t = Table.grid(padding=(0, 2))
        t.add_column(justify="right", style="rtt.muted")
        t.add_column(justify="left")
        c = self.state.counts
        t.add_row("refused",  Text(str(c.get("refused", 0)),  style="rtt.refused"))
        t.add_row("leaked",   Text(str(c.get("leaked", 0)),   style="rtt.leaked"))
        t.add_row("partial",  Text(str(c.get("partial", 0)),  style="rtt.partial"))
        t.add_row("skipped",  Text(str(c.get("skipped", 0)),  style="rtt.skipped"))
        t.add_row("error",    Text(str(c.get("error", 0)),    style="rtt.error"))
        return t

    def _meta(self) -> Table:
        t = Table.grid(padding=(0, 2))
        t.add_column(justify="right", style="rtt.muted")
        t.add_column(justify="left")
        t.add_row("target", self.state.target)
        t.add_row("model",  self.state.model)
        t.add_row("total",  str(self.state.total))
        t.add_row("done",   f"{self.state.completed}/{self.state.total}")
        return t

    def _activity_panel(self) -> Panel:
        if not self.state.activity:
            body: RenderableType = Text(
                "(no probes yet — warming up)",
                style="rtt.muted",
            )
        else:
            body = Group(*[Text.from_markup(line) for line in self.state.activity])
        return Panel(
            body,
            title="[rtt.heading]activity[/]",
            border_style="rtt.border",
            padding=(0, 1),
        )

    def _progress_bar(self) -> Progress:
        if self._progress is None:
            self._progress = Progress(
                SpinnerColumn(style="rtt.spider"),
                TextColumn("[rtt.heading]{task.description}[/]"),
                BarColumn(bar_width=None, complete_style="rtt.web",
                          finished_style="rtt.refused"),
                TaskProgressColumn(),
                TextColumn("[rtt.muted]elapsed[/]"),
                TimeElapsedColumn(),
                expand=True,
                console=self.console,
            )
            self._task_id = self._progress.add_task(
                "probing", total=max(self.state.total, 1),
            )
        # Sync the visible progress with the state.
        self._progress.update(self._task_id, completed=self.state.completed,
                              total=max(self.state.total, 1))
        return self._progress

    def _layout(self) -> Layout:
        layout = Layout()
        layout.split_column(
            Layout(self._progress_bar(), size=3, name="progress"),
            Layout(name="middle", ratio=1),
        )
        layout["middle"].split_row(
            Layout(self._activity_panel(), name="activity", ratio=2),
            Layout(
                Panel(
                    Group(self._meta(), Text(""), self._scoreboard()),
                    title="[rtt.heading]scorecard[/]",
                    border_style="rtt.border",
                    padding=(0, 1),
                ),
                name="scorecard",
                ratio=1,
            ),
        )
        return layout

    # ------- live driver ------------------------------------------------

    def live(self) -> Live:
        """Return a Rich ``Live`` context manager bound to this dashboard.

        We refresh manually — driven by the harness — rather than letting
        Rich's background thread tick, because async + background threads
        is exactly the recipe for the "why is my test flaky" mystery."""
        return Live(
            self._layout(),
            console=self.console,
            refresh_per_second=10,  # Live's own redraw cap; we still drive ticks
            transient=False,
            auto_refresh=False,
        )

    def render_into(self, live: Live) -> None:
        """Re-render after state has changed. Cheap enough to call on every
        probe completion."""
        live.update(self._layout(), refresh=True)


# ---------------------------------------------------------------------------
# Standalone smoke test — run `python -m tui.dashboard` to see it animate.
# ---------------------------------------------------------------------------
if __name__ == "__main__":  # pragma: no cover
    import random
    import time

    state = DashboardState(
        target="openrouter",
        model="anthropic/claude-haiku-4-5",
        total=20,
    )
    dash = Dashboard(state)
    cats = ["LLM01", "LLM02", "LLM06", "LLM08", "JAIL"]
    outs = ["refused", "refused", "refused", "leaked", "partial", "error"]
    with dash.live() as live:
        for i in range(20):
            time.sleep(0.18)
            state.record(
                probe_id=f"p_{i:02d}_inj",
                category=random.choice(cats),  # nosec B311
                outcome=random.choice(outs),   # nosec B311
            )
            dash.render_into(live)
    print()
    print("smoke test ok.")
