# Ethical Use Policy

This toolkit exists so that defenders can test LLM deployments **they own
or have written authorisation to test**. That sentence is the entire
policy. The rest of this document just spells out what it means in
practice.

```
                           .
                          /|\
                         / | \
                        /  |  \
                       /   |   \
                      /    |    \
                  .--/-----+-----\--.
                 ( ( WARNING SHOT ) )
                  '-----------+----'
                              |
              "we test our own roof, not the neighbour's."
```

## Enforcement in the tool

This is policy backed by a runtime gate, not policy-as-prose alone. A
**live** `rtt scan` refuses to start until you attest authorization:

- pass `--authorized` on the command line, or
- answer the interactive confirmation prompt, or
- set `RTT_ASSUME_AUTHORIZED=1` for trusted automation.

In a non-interactive context (CI, pipe) with none of the above, the scan
exits non-zero without sending a single probe. `--dry-run` is exempt
because it performs no network I/O.

## In scope

- LLM endpoints **you** operate.
- LLM endpoints **your employer** operates and has asked you to assess.
- LLM endpoints with a **published vulnerability-disclosure programme**
  whose terms cover automated probing.
- Local models you run yourself (Ollama, vLLM, llama.cpp, etc.).
- Models you access through paid API providers, **only at probe rates
  consistent with the provider's terms of service**. The default config
  in this repo runs each probe **once** for that reason.

## Out of scope

- Probing third-party LLM applications without permission.
- Using probe responses as a stepping-stone to attack downstream
  systems (the scorer flags potentially-exploitable outputs; the
  toolkit does not weaponise them).
- Using this toolkit to generate, distribute, or refine adversarial
  prompts for offensive use against systems you do not own.
- Training derivative jailbreaks against the responses captured here.

## What the probes actually are

Each probe tests for the **presence of a vulnerability category**, not
a weaponised attack. For example:

- The **prompt-injection** probes ask the model to ignore a (synthetic)
  system prompt that the toolkit sets in the request itself. There is
  no real victim system being attacked; the test target *is* the
  controlled environment.
- The **sensitive-information** probes look for whether the model will
  reveal canary strings or fabricated PII inserted into the same
  request. They do not extract real data.
- The **excessive-agency** probes describe hypothetical tool-use
  scenarios; they do not execute any real tools.

This is an important distinction. The toolkit is a **vulnerability
scanner**, not an exploit framework. It tells you *whether* a category
of weakness exists; deciding what to do with that finding is your
problem (and your responsibility).

## Responsible disclosure

If you find a vulnerability in a deployment using this toolkit, follow
the deployment owner's disclosure process. If they don't have one:

1. Document the finding (the toolkit's JSON report is suitable).
2. Contact the owner privately, give them a reasonable window
   (typically 90 days) to fix it before any public discussion.
3. Do not share the probe responses publicly until then.

If you find a bug in **the toolkit itself**, open an issue on the
GitHub repository or email `alibhutto101112@gmail.com`.

## On running this against major API providers

OpenRouter, NVIDIA NIM, OpenAI, and Anthropic all permit reasonable
adversarial-robustness research against their hosted models, subject to
rate limits and their respective terms of service. If you run this
toolkit against those endpoints:

- Use your own API key. The repository contains no credentials.
- Respect the provider's rate limits. The default sample run takes
  under 200 probe executions across a session; that is well within
  free-tier quotas for most providers.
- Do not republish the providers' raw responses in a way that
  competes with their service or reveals system-prompt material that
  the provider has not chosen to disclose.

## Final note

Red-teaming exists to make systems safer. If a probe in this toolkit
strikes you as gratuitous, mean, or only useful for harm, please open
an issue: it should probably be removed. The line between "tests for a
vulnerability" and "is the vulnerability" is one I take seriously, and
patches that move probes back across that line are welcome.

---

~ Ali Murtaza Bhutto / ORCID 0009-0007-2787-943X / 2026
