"""
Static checks on the probe registry.

These tests don't need an LLM at all — they just sanity-check that
every shipped probe is well-formed, has unique ids, and respects the
contracts that the scorer and report writers depend on.
"""

from __future__ import annotations

import pytest

from probes import all_probes, by_category
from probes.base import Probe, Severity, VALID_CATEGORIES


def test_exactly_47_probes_registered():
    # The CV/badge claim. Don't ship a regression on this without thinking.
    assert len(all_probes()) == 47


def test_every_owasp_category_covered():
    cats = {p.category for p in all_probes()}
    expected = {f"LLM{i:02d}" for i in range(1, 11)} | {"JAIL"}
    assert expected.issubset(cats), f"missing categories: {expected - cats}"


def test_no_duplicate_probe_ids():
    ids = [p.id for p in all_probes()]
    assert len(ids) == len(set(ids))


def test_all_categories_valid():
    for p in all_probes():
        assert p.category in VALID_CATEGORIES


def test_all_payloads_nonempty():
    for p in all_probes():
        assert p.payload.strip(), f"probe {p.id} has empty payload"


def test_all_severities_set():
    for p in all_probes():
        assert isinstance(p.severity, Severity)


def test_id_format_is_dotted_lowercase():
    for p in all_probes():
        assert p.id == p.id.lower(), f"{p.id}: must be lowercase"
        assert "." in p.id, f"{p.id}: must contain a dot"


def test_jailbreaks_have_jail_category():
    jails = by_category("JAIL")
    assert len(jails) == 8
    for p in jails:
        assert p.category == "JAIL"


def test_probe_distribution_matches_documented_counts():
    from collections import Counter
    counts = Counter(p.category for p in all_probes())
    assert dict(counts) == {
        "LLM01": 5, "LLM02": 4, "LLM03": 3, "LLM04": 4, "LLM05": 3,
        "LLM06": 5, "LLM07": 4, "LLM08": 4, "LLM09": 4, "LLM10": 3,
        "JAIL": 8,
    }


def test_id_prefix_matches_category():
    for p in all_probes():
        prefix = p.id.split(".", 1)[0]
        assert prefix == p.category.lower(), (
            f"{p.id}: id prefix must equal category {p.category!r}"
        )


def test_probe_immutability():
    p = all_probes()[0]
    with pytest.raises(Exception):
        p.id = "spoofed"  # type: ignore[misc]  -- frozen dataclass


def test_probe_rejects_invalid_category():
    with pytest.raises(ValueError):
        Probe(
            id="x.y", category="LLM99", title="bad", payload="hi",
            expected_behavior="-",
        )


def test_probe_rejects_empty_payload():
    with pytest.raises(ValueError):
        Probe(
            id="x.y", category="LLM01", title="bad", payload="   \n",
            expected_behavior="-",
        )
