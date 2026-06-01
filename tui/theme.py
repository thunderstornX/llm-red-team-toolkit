"""
The toolkit's colour theme.

We pick from the 16 ANSI colours rather than truecolor RGB so the TUI
looks correct in tmux, screen, and over SSH on the kind of jump box
that hasn't been updated since 2014. (The kind of jump box that needs
red-teaming, in other words.)

   "the only thing more depressing than a bad colour scheme is a
    pretty one that turns into mud when you SSH in over PuTTY."
                                                  -- nobody, but true.
"""

from __future__ import annotations

from rich.console import Console
from rich.theme import Theme

# Each style is a *semantic* role, not a colour. That way if we redesign
# we change one entry and the whole TUI follows.
THEME = Theme({
    # core spider-web reds
    "rtt.title":       "bold red",
    "rtt.spider":      "bright_red",
    "rtt.web":         "red",
    "rtt.tagline":     "italic dim",
    "rtt.signature":   "dim",
    # scoring outcomes
    "rtt.refused":     "bold green",       # model refused the bait. good.
    "rtt.leaked":      "bold red",         # model walked into it. bad.
    "rtt.partial":     "bold yellow",      # mixed signal. needs human eyes.
    "rtt.skipped":     "dim",
    "rtt.error":       "bold magenta",     # adapter / network problem
    "rtt.warn":        "bold yellow",      # authorization / caution prompts
    # category badges
    "rtt.cat.llm01":   "bright_red",
    "rtt.cat.llm02":   "red",
    "rtt.cat.llm03":   "yellow",
    "rtt.cat.llm04":   "bright_yellow",
    "rtt.cat.llm05":   "green",
    "rtt.cat.llm06":   "bright_green",
    "rtt.cat.llm07":   "cyan",
    "rtt.cat.llm08":   "bright_cyan",
    "rtt.cat.llm09":   "blue",
    "rtt.cat.llm10":   "bright_blue",
    "rtt.cat.jail":    "magenta",
    # severity tones
    "rtt.sev.crit":    "bold red on white",
    "rtt.sev.high":    "bold red",
    "rtt.sev.med":     "yellow",
    "rtt.sev.low":     "dim",
    # framing
    "rtt.border":      "red",
    "rtt.heading":     "bold",
    "rtt.muted":       "dim",
    "rtt.kbd":         "reverse",
})


# A single shared Console keeps width detection consistent across the
# program; passing console=foo into every Panel/Table/Progress is just
# noise. We export it from tui/__init__.py.
console = Console(theme=THEME, highlight=False)
