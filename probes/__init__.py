"""
The probe library.

Each module maps to an OWASP LLM Top 10 (2025) category (a couple of
categories span two modules), plus a cross-cutting jailbreaks module.
Importing the package registers all probes by side-effect — that's how
``registry.all_probes()`` finds them.

If you add a new module here, also add it to the explicit import list
below. The list is explicit on purpose: glob-based auto-import has
bitten me once too often.
"""

from probes import (  # noqa: F401  -- imported for side-effects
    data_model_poisoning,
    excessive_agency,
    improper_output,
    jailbreaks,
    misinformation,
    model_extraction,
    prompt_injection,
    sensitive_info,
    supply_chain,
    system_prompt_leakage,
    tool_abuse,
    unbounded_consumption,
    vector_embedding,
)
from probes.base import Probe, ProbeResult, Severity
from probes.registry import all_probes, by_category, get_probe

__all__ = [
    "Probe",
    "ProbeResult",
    "Severity",
    "all_probes",
    "by_category",
    "get_probe",
]
