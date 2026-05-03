"""
TUI smoke tests. We don't try to assert pixel-perfect output — we just
prove that the renderables build without exceptions and that the
banner text contains the project signature.
"""

from __future__ import annotations

from io import StringIO

from rich.console import Console

from tui.banner import BANNER, render_banner, render_compact_banner
from tui.dashboard import Dashboard, DashboardState
from tui.report import render_full, render_summary
from tui.theme import THEME


def _captured() -> Console:
    """A captured Console with our theme baked in. Without the theme,
    every "rtt.foo" style markup blows up MissingStyle."""
    return Console(file=StringIO(), width=100, force_terminal=False,
                   record=True, no_color=True, theme=THEME)


def test_banner_contains_signature():
    assert "ORCID 0009-0007-2787-943X" in BANNER
    assert "L L M" in BANNER
    assert "OWASP" in BANNER


def test_render_banner_no_exceptions():
    c = _captured()
    render_banner(target_console=c)
    out = c.export_text()
    assert "rtt" in out.lower()
    assert "OWASP" in out


def test_render_compact_banner():
    c = _captured()
    render_compact_banner(target_console=c)
    out = c.export_text()
    assert "rtt v1.0" in out


def test_dashboard_records_outcomes():
    state = DashboardState(target="t", model="m", total=3)
    state.record("p1", "LLM01", "refused")
    state.record("p2", "LLM01", "leaked")
    state.record("p3", "JAIL", "partial")
    assert state.completed == 3
    assert state.counts["refused"] == 1
    assert state.counts["leaked"] == 1
    assert state.counts["partial"] == 1


def test_dashboard_layout_renders():
    state = DashboardState(target="t", model="m", total=10)
    state.record("p1", "LLM01", "refused")
    c = _captured()
    dash = Dashboard(state, console=c)
    layout = dash._layout()
    c.print(layout)
    # As long as we didn't throw, we're done.
    assert "t" in c.export_text() or "m" in c.export_text()


def test_render_summary():
    c = _captured()
    counts = {"refused": 8, "leaked": 1, "partial": 1, "skipped": 0, "error": 0}
    render_summary(target="t", model="m", counts=counts, elapsed_s=5.0,
                   console=c)
    out = c.export_text()
    assert "scan complete" in out


def test_render_full_groups_by_category():
    rs = [
        {"id": "a.1", "category": "LLM01", "severity": "high",
         "outcome": "refused", "confidence": 0.9, "notes": ""},
        {"id": "b.1", "category": "JAIL", "severity": "med",
         "outcome": "leaked", "confidence": 0.8, "notes": "x"},
    ]
    c = _captured()
    render_full(rs, console=c)
    out = c.export_text()
    assert "LLM01" in out
    assert "JAIL" in out
