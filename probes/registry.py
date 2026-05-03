"""
Probe registry: the global lookup table.

Each probe module imports ``register`` from here and calls it once per
probe at import time. The registry is a plain dict keyed on probe id,
which means double-registration raises immediately — typo-driven id
collisions are caught the moment you run anything.
"""

from __future__ import annotations

from typing import Iterable, Optional

from probes.base import Probe

_REGISTRY: dict[str, Probe] = {}


def register(probe: Probe) -> Probe:
    """Add a probe to the registry. Returns the probe so the call can
    be used as a decorator-ish one-liner in module bodies."""
    if probe.id in _REGISTRY:
        raise ValueError(
            f"duplicate probe id: {probe.id!r}. "
            f"already registered as {_REGISTRY[probe.id].title!r}."
        )
    _REGISTRY[probe.id] = probe
    return probe


def all_probes() -> list[Probe]:
    """All probes currently registered, in registration order. Stable
    so reports diff cleanly across runs."""
    return list(_REGISTRY.values())


def by_category(category: str) -> list[Probe]:
    return [p for p in _REGISTRY.values() if p.category == category]


def get_probe(probe_id: str) -> Optional[Probe]:
    return _REGISTRY.get(probe_id)


def filter_probes(
    *,
    categories: Optional[Iterable[str]] = None,
    tags: Optional[Iterable[str]] = None,
) -> list[Probe]:
    """Subset by category and/or tag. Empty filter list == no filter."""
    cat_set = set(categories) if categories else None
    tag_set = set(tags) if tags else None
    out: list[Probe] = []
    for p in _REGISTRY.values():
        if cat_set is not None and p.category not in cat_set:
            continue
        if tag_set is not None and not (set(p.tags) & tag_set):
            continue
        out.append(p)
    return out


def _reset_for_tests() -> None:
    """Internal: tests that exercise the registry need a clean slate.
    Production code never calls this."""
    _REGISTRY.clear()
