"""
Shared pytest fixtures.

Importing ``probes`` triggers side-effect registration of every probe.
We do that once per session so individual tests can lean on the
populated registry without paying for re-imports.
"""

from __future__ import annotations

import pytest


@pytest.fixture(scope="session", autouse=True)
def _load_probes():
    """Register all probes exactly once for the session."""
    import probes  # noqa: F401  -- side-effect import
    yield
