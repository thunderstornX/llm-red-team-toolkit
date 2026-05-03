"""
The probe library.

Each module in this package is one OWASP LLM Top 10 (2025) category,
plus a cross-cutting jailbreaks module. Importing the package registers
all probes by side-effect — that's how ``registry.all_probes()`` finds
them.

If you add a new module here, also add it to ``_AUTOREGISTER`` below.
The list is explicit on purpose: glob-based auto-import has bitten me
once too often.
"""

from probes import (  # noqa: F401  -- imported for side-effects
    excessive_agency,
    insecure_output,
    insecure_plugin,
    jailbreaks,
    model_dos,
    model_theft,
    overreliance,
    prompt_injection,
    sensitive_info,
    supply_chain,
    training_data,
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
