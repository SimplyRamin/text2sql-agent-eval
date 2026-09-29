# Results

## Comparison table

| Architecture | Overall | T1 | T2 | T3 | T4 | T5 | Cost (100 q) | Latency (mean / median) |
|---|---|---|---|---|---|---|---|---|
| **Local** — dumb baseline | 59% | 100% | 76% | 32% | 52% | 60% | $0 | not instrumented* |
| **Local** — agent (retrieval + retry) | 58% | 100% | 64% | 40% | 52% | 60% | $0 | not instrumented* |
| **Local** — routed agent | **63%** | 100% | 76% | 52% | 44% | 66.7% | $0 | 20.7s / 15.3s |
| **Hosted** (gpt-4o-mini) — dumb baseline | **71%** | 100% | 88% | 60% | 44% | 86.7% | $0.0099 | 1.3s / 1.4s |
| **Hosted** (gpt-4o-mini) — routed agent | 70% | 100% | 80% | 60% | 48% | 86.7% | $0.0416 | 5.8s / 4.3s |

\* Latency instrumentation was added in Phase 6; the two earliest local
runs predate it and were never re-run purely to backfill timing data —
noted rather than estimated.

Local model: Qwen2.5-Coder-7B via Ollama, RTX 3050 (6GB VRAM). Hosted
model: gpt-4o-mini via AvalAI (OpenAI-compatible gateway, pricing matches
official OpenAI rates). All numbers are single runs; retry temperature
(0.4) makes results non-deterministic on close cases — treat as
accuracy ± some variance, not exact figures (see `FAILURE_TAXONOMY.md`
§6).

## What the numbers show

**Schema retrieval and capped self-correction alone made things slightly
worse, not better** (58% vs 59% baseline) — until routing to
specialist prompts fixed the specific failure modes retrieval and retry
couldn't touch on their own (fan-out/dedup errors, category-translation
over-joins), at which point the same architecture reached 63%, the best
local result. Tier 3 — three-and-more-table joins, the hardest and most
failure-prone category from the start — improved the most across every
phase: 32% → 40% → 52%, a +20pp arc from baseline to the final local
architecture, driven by two concrete interventions (explicit join-key
hints, a join-path-reasoning instruction) each validated against real
question IDs, not assumed.

**The hosted model (gpt-4o-mini) beat every local result outright** — no
surprise given the capability gap, but the more interesting finding is
that **routing slightly *hurt* on the hosted model** (70% vs 71% baseline),
the inverse of the local result. The most likely explanation: the
specialist join-prompt's reasoning instruction, built and tuned against
Qwen2.5-Coder-7B's specific weaknesses, appears to occasionally push a
more capable model toward unnecessary structural complexity it didn't
need in the first place (see `FAILURE_TAXONOMY.md` §4) — a genuine,
non-obvious tradeoff between model-specific tuning and architecture
generalization, not something this project set out to prove either way.

**Cost and latency tell their own story.** Hosted inference cost about a
nickel total for both full 100-question runs combined — negligible in
absolute terms, but the routed agent used roughly 4x the tokens of the
plain baseline for a net *accuracy loss*, purely because of the extra
retries and longer specialist prompts. Locally, the routed agent averaged
~21 seconds per question versus hosted's ~1.3-5.8 seconds — a real
practical tradeoff between $0 inference and response time that would
matter in any actual deployment decision.

Full failure-mode breakdown: see `FAILURE_TAXONOMY.md`.