"""
Harness: orchestration, scoring, reporting, CLI.

The package boundary between ``harness`` and ``probes`` is meaningful:
``probes`` is a static catalog of attack descriptions, ``harness`` is
everything that *executes* those probes against a target. If a future
contributor wants to add a probe, they touch ``probes/``. If they want
to add a target adapter, they touch ``adapters/``. If they want to
change how scoring works, this is the place.
"""
