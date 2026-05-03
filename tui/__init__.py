"""
TUI module: Rich-powered terminal UI for the red-team harness.

Everything in here is for *humans looking at terminals*. Anything that
needs to be machine-parsed lives elsewhere (see ``harness/report.py`` for
JSON output). Mixing the two is how you end up with ANSI codes in your
log shipper.
"""

from tui.banner import BANNER, render_banner, render_compact_banner
from tui.theme import THEME, console

__all__ = [
    "BANNER",
    "render_banner",
    "render_compact_banner",
    "THEME",
    "console",
]
