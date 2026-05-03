"""
Probe and ProbeResult: the two dataclasses every other module uses.

A *Probe* is a static description of an attack to attempt. It is pure
data — no I/O, no side effects, no network. The evaluator picks them up
from ``registry``, sends them through an adapter, and the adapter
returns a *ProbeResult*.

Why dataclasses and not Pydantic models for these? Two reasons:

    1. Probes ship with the package. They must never trigger a runtime
       Pydantic validation cost; they're loaded thousands of times.
    2. Results are written to disk and re-read for reporting. Pydantic
       v2 is lovely but the conversion churn for read-mostly objects
       like these is overkill.

Pydantic *is* used at the network boundaries (adapters, CLI input).
That's where validation actually matters.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Optional


class Severity(str, Enum):
    """How bad is it if the model walks into this probe?

    Severity is a property of the *probe*, not of any one outcome.
    A "REFUSED" outcome on a CRITICAL probe still counts as a clean
    pass; a "LEAKED" outcome on a LOW probe is still a finding worth
    reading.
    """
    LOW = "low"
    MED = "med"
    HIGH = "high"
    CRIT = "crit"


# Keep this list in sync with tui.report.CATEGORY_LABELS.
VALID_CATEGORIES = frozenset({
    "LLM01", "LLM02", "LLM03", "LLM04", "LLM05",
    "LLM06", "LLM07", "LLM08", "LLM09", "LLM10",
    "JAIL",
})


@dataclass(frozen=True)
class Probe:
    """A static probe definition.

    Fields:
        id:
            Stable identifier. Format: ``<category-lower>.<short-tag>``,
            e.g. ``llm01.direct_override``. Stable across versions.
            **Never reuse an id**; results referenced by id need to mean
            the same thing forever.
        category:
            One of the OWASP codes (LLM01..LLM10) or "JAIL".
        title:
            Short human-readable name. Shown in tables.
        payload:
            The actual prompt to send. Multi-line is fine.
        expected_behavior:
            Plain-English description of what a well-aligned model should
            do here. Read by humans during review; not parsed.
        severity:
            See ``Severity``.
        success_markers:
            Substrings that, if present in the response (case-insensitive),
            indicate the probe *succeeded* — i.e., the model walked into
            it. Matched by the scorer.
        refusal_markers:
            Substrings that, if present, indicate refusal. The scorer has
            its own broad refusal-detection regex; these are
            probe-specific *additions*.
        tags:
            Free-form labels, e.g. ``("encoding", "rot13")``. Used for
            filtering in the CLI (``--tags rot13``).
    """
    id: str
    category: str
    title: str
    payload: str
    expected_behavior: str
    severity: Severity = Severity.MED
    success_markers: tuple[str, ...] = field(default_factory=tuple)
    refusal_markers: tuple[str, ...] = field(default_factory=tuple)
    tags: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.category not in VALID_CATEGORIES:
            raise ValueError(
                f"probe {self.id!r}: unknown category {self.category!r}. "
                f"valid: {sorted(VALID_CATEGORIES)}"
            )
        if not self.id or " " in self.id:
            raise ValueError(f"probe id must be non-empty and space-free: {self.id!r}")
        if not self.payload.strip():
            raise ValueError(f"probe {self.id!r}: empty payload")


# An "outcome" is what the scorer assigned. Strings rather than an enum
# because they get serialised to JSON / written to humans / matched in
# Markdown tables a lot — a string is the cheapest representation.
Outcome = str  # one of: "refused" | "leaked" | "partial" | "skipped" | "error"


@dataclass
class ProbeResult:
    """One probe execution.

    Returned by the evaluator, consumed by the report writers.

    ``response`` holds the raw model output. The toolkit stores it
    in-memory and on disk in the JSON report so reviewers can audit
    the scorer's classifications. If your deployment forbids retaining
    raw model output, run with ``--no-record-responses`` (the CLI has
    a flag for this, and the JSON writer redacts on its way to disk).
    """
    probe_id: str
    category: str
    severity: str
    payload_sent: str
    response: str
    outcome: Outcome
    confidence: float            # 0.0 (low) -> 1.0 (high)
    notes: str = ""
    latency_ms: int = 0
    error: Optional[str] = None  # populated when outcome == "error"

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        # The "id" key is what the report renderer uses; alias for clarity.
        d["id"] = d.pop("probe_id")
        return d

    @classmethod
    def skipped(cls, probe: Probe, reason: str) -> "ProbeResult":
        return cls(
            probe_id=probe.id, category=probe.category, severity=probe.severity.value,
            payload_sent=probe.payload, response="",
            outcome="skipped", confidence=0.0, notes=reason,
        )

    @classmethod
    def errored(cls, probe: Probe, error: str) -> "ProbeResult":
        return cls(
            probe_id=probe.id, category=probe.category, severity=probe.severity.value,
            payload_sent=probe.payload, response="",
            outcome="error", confidence=0.0,
            notes="adapter / network error", error=error,
        )
