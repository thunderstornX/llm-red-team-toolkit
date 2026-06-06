"""
CLI + authorization-gate tests.

The live-scan authorization gate (``--authorized`` / interactive prompt /
``RTT_ASSUME_AUTHORIZED``) is the headline safety feature, so every
branch of it is pinned here — both as unit calls into
``_require_authorization`` and end-to-end through the Typer app. The
dry-run and no-match exit paths are covered too.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
import typer

from harness import cli
from harness.config import TargetConfig


def _target() -> TargetConfig:
    return TargetConfig(adapter="generic", model="m", base_url="http://x/v1")


def _force_tty(monkeypatch, is_tty: bool) -> None:
    monkeypatch.setattr(cli.sys, "stdin", SimpleNamespace(isatty=lambda: is_tty))


# ---- _require_authorization: every branch ------------------------------

def test_authorized_flag_passes_gate(monkeypatch):
    monkeypatch.delenv("RTT_ASSUME_AUTHORIZED", raising=False)
    # No exception == gate passed.
    cli._require_authorization(_target(), authorized=True)


def test_env_assume_authorized_passes_gate(monkeypatch):
    monkeypatch.setenv("RTT_ASSUME_AUTHORIZED", "1")
    cli._require_authorization(_target(), authorized=False)


def test_wrong_env_value_does_not_pass_gate(monkeypatch):
    monkeypatch.setenv("RTT_ASSUME_AUTHORIZED", "true")  # only exact "1" counts
    _force_tty(monkeypatch, False)
    with pytest.raises(typer.Exit) as ei:
        cli._require_authorization(_target(), authorized=False)
    assert ei.value.exit_code == 4


def test_noninteractive_without_authorization_is_refused(monkeypatch):
    monkeypatch.delenv("RTT_ASSUME_AUTHORIZED", raising=False)
    _force_tty(monkeypatch, False)
    with pytest.raises(typer.Exit) as ei:
        cli._require_authorization(_target(), authorized=False)
    assert ei.value.exit_code == 4


def test_interactive_confirm_yes_passes(monkeypatch):
    monkeypatch.delenv("RTT_ASSUME_AUTHORIZED", raising=False)
    _force_tty(monkeypatch, True)
    monkeypatch.setattr(cli.typer, "confirm", lambda *a, **k: True)
    cli._require_authorization(_target(), authorized=False)


def test_interactive_confirm_no_is_refused(monkeypatch):
    monkeypatch.delenv("RTT_ASSUME_AUTHORIZED", raising=False)
    _force_tty(monkeypatch, True)
    monkeypatch.setattr(cli.typer, "confirm", lambda *a, **k: False)
    with pytest.raises(typer.Exit) as ei:
        cli._require_authorization(_target(), authorized=False)
    assert ei.value.exit_code == 4


# ---- end-to-end through the Typer app ----------------------------------

def test_scan_noninteractive_blocks_before_network(cli_runner, tmp_path, monkeypatch):
    # No --authorized, non-interactive stdin -> exit 4, raised before any
    # adapter is built or any socket is opened.
    monkeypatch.delenv("RTT_ASSUME_AUTHORIZED", raising=False)
    res = cli_runner.invoke(cli.app, [
        "scan", "--adapter", "generic", "--base-url", "http://127.0.0.1:9/v1",
        "--model", "m", "--output-dir", str(tmp_path), "--quiet",
    ])
    assert res.exit_code == 4


def test_scan_no_matching_probes_exits_2(cli_runner, tmp_path):
    res = cli_runner.invoke(cli.app, [
        "scan", "--adapter", "generic", "--base-url", "http://x/v1",
        "--model", "m", "--tag", "no_such_tag_exists",
        "--output-dir", str(tmp_path), "--quiet",
    ])
    assert res.exit_code == 2


def test_dry_run_writes_reports_without_network(cli_runner, tmp_path):
    res = cli_runner.invoke(cli.app, [
        "scan", "--adapter", "generic", "--base-url", "http://x/v1",
        "--model", "m", "--category", "LLM01", "--dry-run",
        "--output-dir", str(tmp_path), "--quiet",
    ])
    assert res.exit_code == 0, res.output
    assert (tmp_path / "generic_m.json").exists()
    assert (tmp_path / "generic_m.md").exists()


def test_list_command_runs(cli_runner):
    res = cli_runner.invoke(cli.app, ["list", "--category", "LLM01", "--quiet"])
    assert res.exit_code == 0
    assert "llm01." in res.output
