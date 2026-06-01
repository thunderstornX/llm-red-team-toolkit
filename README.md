# llm-red-team-toolkit

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20480444.svg)](https://doi.org/10.5281/zenodo.20480444)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-49%20passing-brightgreen)](#tests)
[![Probes](https://img.shields.io/badge/probes-47-red)](#probes)
[![OWASP](https://img.shields.io/badge/OWASP%20LLM%20Top%2010-2025-blue)](https://owasp.org/www-project-top-10-for-large-language-model-applications/)

```
        ____    ______  ______                       \   |   /
       / __ \  /_  __/ /_  __/                       \\\\|////
      / /_/ /   / /     / /                       ──── [ ● ] ────
     / _, _/   / /     / /                            ////|\\\\
    /_/ |_|   /_/     /_/                            /   /|\   \

        L L M    R E D    T E A M    T O O L K I T
                     OWASP LLM Top 10 (2025)
                probe  ·  sting  ·  report  ·  disclose

           ~ AMB · ORCID 0009-0007-2787-943X · v1.0 · 2026 ~
```

A Python harness that systematically probes a Large Language Model
deployment against the **OWASP Top 10 for LLM Applications (2025)**.
**47 probes** across all ten categories plus **8 cross-cutting
jailbreaks**, three target adapters (OpenRouter, NVIDIA NIM, generic
OpenAI-compatible), a deterministic heuristic scorer (no LLM-as-judge),
and a Rich-powered terminal UI.

> **The spider is the harness. The web is the OWASP Top 10. Anything
> that flies in is the model under test.**

---

## See it run

`rtt scan` opens a live dashboard with progress, streaming activity,
and a running scorecard:

![dashboard](paper/figures/dashboard.png)

When the scan completes, you get a clean verdict:

![summary](paper/figures/summary.png)

Filter the probe library on the way in:

![list](paper/figures/list.png)

---

## Quickstart

```bash
git clone https://github.com/thunderstornX/llm-red-team-toolkit.git
cd llm-red-team-toolkit
pip install -r requirements-dev.txt

# 1. against a hosted model on OpenRouter
export OPENROUTER_API_KEY=sk-or-...
python -m harness.cli scan \
    --adapter openrouter \
    --model anthropic/claude-haiku-4-5

# 2. against a local Ollama (any OpenAI-compat endpoint)
ollama serve &
ollama pull qwen2.5:0.5b
python -m harness.cli scan \
    --adapter generic \
    --base-url http://localhost:11434/v1 \
    --model qwen2.5:0.5b

# 3. against an NVIDIA NIM endpoint
export NVIDIA_API_KEY=nvapi-...
python -m harness.cli scan \
    --adapter nvidia \
    --model meta/llama-3.3-70b-instruct
```

Filter, dry-run, parallelise:

```bash
# only the LLM01 probes:
python -m harness.cli scan --adapter openrouter --category LLM01

# only base64-smuggling probes:
python -m harness.cli scan --adapter openrouter --tag base64

# build the report from synthetic responses (no network):
python -m harness.cli scan --adapter openrouter --dry-run

# 8-way parallel:
python -m harness.cli scan --adapter openrouter --concurrency 8
```

---

## What's in the box

```
.
├── probes/                # 47 probes, registered at import time
│   ├── prompt_injection.py    LLM01: direct, indirect, leak, role, delim
│   ├── insecure_output.py     LLM02: markdown, html, sql, path
│   ├── training_data.py       LLM03: trigger, copyright, canary
│   ├── model_dos.py           LLM04: recursion, unicode, flood, nesting
│   ├── supply_chain.py        LLM05: identity, cutoff, deps
│   ├── sensitive_info.py      LLM06: pii, system-prompt, recall, cred, re-id
│   ├── insecure_plugin.py     LLM07: shell, schema, cross-plugin, persist
│   ├── excessive_agency.py    LLM08: unauth, scope-creep, persist, coerce
│   ├── overreliance.py        LLM09: hallucinate, citation, legal, calib
│   ├── model_theft.py         LLM10: fingerprint, distil, architecture
│   └── jailbreaks.py          JAIL: dan, b64, rot13, leet, reverse, multi-turn,
│                                    context-flood, prefix-injection
├── adapters/              # async OpenAI-compatible HTTP clients
│   ├── openrouter.py
│   ├── nvidia.py
│   └── generic.py
├── harness/               # orchestration
│   ├── cli.py                  Typer CLI
│   ├── evaluator.py            async dispatcher with bounded concurrency
│   ├── scorer.py               heuristic refusal/leak/partial classifier
│   ├── report.py               JSON + Markdown writers
│   └── config.py               Pydantic target / run config
├── tui/                   # Rich-powered terminal UI
│   ├── banner.py               the spider
│   ├── theme.py                colour theme
│   ├── dashboard.py            live progress + activity + scorecard
│   └── report.py               post-run rendering
├── tests/                 # 49 pytest cases (run in 0.57 s)
├── results/               # sample run captured against qwen2.5:0.5b
│   ├── sample_report.json
│   └── sample_report.md
├── paper/                 # IEEE 3-page paper (paper.pdf)
└── scripts/
    ├── render_figures.py       paper figures from a real run
    └── render_terminal.py      ANSI-aware terminal-to-PNG (no webfonts)
```

---

<a id="probes"></a>
## Probe distribution

| Code  | Category                          | # |
|------:|-----------------------------------|--:|
| LLM01 | Prompt Injection                  | 5 |
| LLM02 | Insecure Output Handling          | 4 |
| LLM03 | Training-Data Poisoning           | 3 |
| LLM04 | Model DoS                         | 4 |
| LLM05 | Supply Chain                      | 3 |
| LLM06 | Sensitive Information Disclosure  | 5 |
| LLM07 | Insecure Plugin Design            | 4 |
| LLM08 | Excessive Agency                  | 4 |
| LLM09 | Overreliance                      | 4 |
| LLM10 | Model Theft                       | 3 |
| JAIL  | Jailbreaks (cross-cutting)        | 8 |
| **·** | **Total**                         | **47** |

`python -m harness.cli list` shows them all with severity, tags, and
title.

---

## How scoring works (and why no LLM-as-judge)

For each `(probe, response)` pair, the scorer applies this decision
tree:

1. probe-specific **success marker** matches → **leaked**
2. probe-specific **refusal marker** matches → **refused**
3. generic refusal regex (10 calibrated patterns) matches → **refused**
4. response is empty / whitespace → **skipped**
5. otherwise → **partial** (human review)

Why not use a strong LLM to judge? Two reasons:

1. **Reproducibility.** Same probe + same response should always
   score the same way. Heuristic regex is reproducible; an LLM judge
   is not.
2. **Auditability.** A reviewer who asks "why did this probe count
   as refused?" gets a concrete regex they can read in 200 lines of
   Python — not "trust the bigger model".

The trade is the **partial** bucket: things the rule set can't
classify go to human eyes. We keep that bucket honest.

---

## Real sample run (verifiable, not made up)

`results/sample_report.{json,md}` is the output of a real scan against
**qwen2.5:0.5b** on Ollama, on an Intel Core i5-8250U (16 GB RAM).
47 probes, 333.5 seconds wall-clock.

| outcome | count | of total |
|---|---:|---:|
| refused | 15 | 31.9 % |
| leaked  | 18 | 38.3 % |
| partial | 14 | 29.8 % |
| skipped | 0  | 0.0 %  |
| error   | 0  | 0.0 %  |

The full per-probe breakdown is in
[`results/sample_report.md`](results/sample_report.md).

To reproduce:

```bash
ollama pull qwen2.5:0.5b
python -m harness.cli scan \
    --adapter generic \
    --base-url http://localhost:11434/v1 \
    --model qwen2.5:0.5b
```

---

<a id="tests"></a>
## Tests

49 pytest cases. The full suite runs in **0.57 seconds**.

```bash
python -m pytest tests/ -v
```

Coverage:
- **probe-registry invariants** — no duplicate ids, all categories
  valid, immutability of frozen dataclasses, payload non-empty
- **scorer** — every canonical refusal phrase, success/refusal marker
  priority, generic regex, empty response, latency propagation
- **adapters** — wire format with respx mocks, HTTP-error path,
  parse-error path, **API key leakage assertion**
- **evaluator** — dispatch under concurrency, dry-run, error
  propagation, response truncation
- **report** — JSON schema + Markdown round-trip + pipe-escape
- **TUI** — banner contains signature, dashboard records outcomes,
  report renderers don't blow up

---

## Ethical use

This is a **vulnerability scanner**, not an exploit framework. Run it
only against endpoints you own or have written authorisation to test.
The probes are detectors for vulnerability *categories*, not weaponised
attacks: every probe sets up its own synthetic system prompt and
canary, so a "leak" reveals a string the operator already knows.

Full policy in [`ETHICAL_USE.md`](ETHICAL_USE.md).

---

## Paper

A 3-page IEEE paper describing the architecture, scoring rationale,
and the live demonstration is in
[`paper/paper.pdf`](paper/paper.pdf).

---

## Citing this work

```bibtex
@software{bhutto2026rtt,
  author    = {Bhutto, Ali Murtaza},
  title     = {llm-red-team-toolkit: An OWASP-aligned adversarial probing
               harness for LLM deployments},
  year      = {2026},
  doi       = {10.5281/zenodo.20480444},
  url       = {https://github.com/thunderstornX/llm-red-team-toolkit},
  orcid     = {0009-0007-2787-943X}
}
```

> The DOI above is the **concept DOI** — it always resolves to the latest
> release. Version 1.0.0 is archived at
> [10.5281/zenodo.20480445](https://doi.org/10.5281/zenodo.20480445).

Related work:
- [`secure-python-pipeline-template`](https://github.com/thunderstornX/secure-python-pipeline-template) — the DevSecOps pipeline this repo's CI builds on.
- [`sovereign-llm-quickstart`](https://github.com/thunderstornX/sovereign-llm-quickstart) — the on-prem Ollama stack you can point this toolkit at.

---

## License

MIT &copy; 2026 Ali Murtaza Bhutto

```
                  \   |   /
                  \\\\|////
              ──── [ ● ] ────
                  ////|\\\\
                  /   /|\   \
```

~ AMB · ORCID 0009-0007-2787-943X · v1.0 · 2026 ~
