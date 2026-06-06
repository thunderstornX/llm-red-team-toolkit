"""
The banner. Yes the banner is its own module.

If a security tool ships without a banner, you cannot trust it. The
banner is a load-bearing UX element, the same way the splash screen on
nethack is load-bearing. It tells you the program loaded, it tells you
which version, and it gives you something to look at while the first
HTTP connection is opening.

This banner has a spider in a web. The spider is the harness. The web
is the OWASP LLM Top 10. The model under test is whatever flies in.
Subtle? Maybe. But you're reading the docstring of an ASCII-art module
so you signed up for this.
"""

from __future__ import annotations

from rich.align import Align
from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text

from tui.theme import console as _default_console


# -----------------------------------------------------------------------------
# The banner itself.
#
# Two columns: chunky ASCII title on the left, spider-in-web on the right.
# Hand-laid out. Strict 70-column content budget so it renders cleanly
# inside an 80-col Panel. Don't "fix" the spacing without re-checking.
# -----------------------------------------------------------------------------
BANNER = r"""
        ____    ______  ______                       \   |   /
       / __ \  /_  __/ /_  __/                       \\\\|////
      / /_/ /   / /     / /                       ──── [ ● ] ────
     / _, _/   / /     / /                            ////|\\\\
    /_/ |_|   /_/     /_/                            /   /|\   \

        L L M    R E D    T E A M    T O O L K I T
                     OWASP LLM Top 10 (2025)
                probe  ·  sting  ·  report  ·  disclose

           ~ AMB · ORCID 0009-0007-2787-943X · v1.0 · 2026 ~
"""

# A compact one-liner for `--quiet` mode and CI.
COMPACT = (
    "rtt v1.0  ·  llm-red-team-toolkit  ·  OWASP LLM Top 10 (2025)  ·  AMB"
)

# The tagline rotates. Pick one at boot, like a fortune file. None of
# these are jokes at the *user's* expense; the toolkit's the one being
# self-deprecating here.
TAGLINES = [
    "we test our own roof, not the neighbour's.",
    "if the model can be tricked, this is how you find out.",
    "52 probes, one scorer, no LLM-judges. fully reproducible.",
    "OWASP-aligned. ToS-respecting. ego-free.",
    "the friendly probe library.",
    "kicking the tires before the audit kicks them for you.",
    "a vulnerability scanner, not an exploit framework.",
]


def _colourise(banner: str) -> Text:
    """Apply the theme styles to the banner art.

    We don't try to be clever about parsing — each line is classified
    by what it contains. Coarse, fast, and good enough.
    """
    out = Text()
    for raw_line in banner.splitlines():
        line = raw_line + "\n"
        stripped = raw_line.strip()
        if not stripped:
            out.append(line)
            continue
        # title-row letters: contain "L L M" or other spaced caps
        if "L L M" in raw_line or "T O O L K I T" in raw_line:
            out.append(line, style="rtt.title")
        # the OWASP tagline row + the underline
        elif stripped.startswith("OWASP") or set(stripped) <= {"─"}:
            out.append(line, style="rtt.tagline")
        # the dotted action row
        elif "probe" in raw_line and "sting" in raw_line:
            out.append(line, style="rtt.tagline")
        # the signature row at the very bottom
        elif raw_line.strip().startswith("~ AMB"):
            out.append(line, style="rtt.signature")
        # the blocky ASCII title rows (figlet-style "RTT")
        elif "/" in raw_line and "_" in raw_line and "L L M" not in raw_line:
            out.append(line, style="rtt.title")
        # everything else is web — slashes, dashes, the spider body
        else:
            out.append(line, style="rtt.web")
    return out


def render_banner(target_console: Console | None = None) -> None:
    """Print the full banner. Call once at program start.

    The panel border is red on purpose: red team. (We are a humble
    profession.) Padding above and below gives the spider room to
    breathe; condensed banners always look cramped.
    """
    c = target_console or _default_console
    body = _colourise(BANNER)
    panel = Panel(
        Align.center(body),
        border_style="rtt.border",
        padding=(0, 2),
        title="[rtt.title]rtt[/]",
        title_align="left",
        subtitle="[rtt.signature]press Ctrl-C any time the spider gets too keen[/]",
        subtitle_align="right",
    )
    c.print(panel)


def render_compact_banner(target_console: Console | None = None) -> None:
    """One-line banner for piped output, CI, or `--quiet` runs."""
    c = target_console or _default_console
    c.print(f"[rtt.title]>>[/] [rtt.tagline]{COMPACT}[/]")


def banner_group(tagline_index: int = 0) -> Group:
    """Banner + tagline as a rich-renderable Group. Useful for embedding
    inside a Live() display where a full Panel would be too large."""
    tagline = TAGLINES[tagline_index % len(TAGLINES)]
    return Group(
        _colourise(BANNER),
        Align.center(Text(f'"{tagline}"', style="rtt.tagline")),
    )


if __name__ == "__main__":  # pragma: no cover - manual eyeball test
    render_banner()
    print()
    render_compact_banner()
