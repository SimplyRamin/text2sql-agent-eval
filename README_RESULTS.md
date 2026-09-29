# Results

## Comparison table

| Architecture | Overall | T1 | T2 | T3 | T4 | T5 | Cost (100 q) | Latency (mean / median) |
|---|---|---|---|---|---|---|---|---|
| **Local** — dumb baseline | 66% | 100% | 80% | 40% | 68% | 60% | $0 | not instrumented* |
| **Local** — routed agent | **70%** | 100% | 84% | 60% | 64% | 53.3% | $0 | ~21s / ~15s** |
| **Hosted** (gpt-4o-mini) — dumb baseline | 80% | 100% | 92% | 72% | 64% | 86.7% | ~$0.01 | ~1.3s / ~1.4s** |
| **Hosted** (gpt-4o-mini) — routed agent | **81%** | 100% | 84% | 72% | 72% | 93.3% | ~$0.04 | ~5.8s / ~4.3s** |

\* Latency instrumentation was added in Phase 6; the earliest local run
predates it.
\*\* Cost/latency figures are from each architecture's first fresh run
(Phase 6/7) — scoring was later corrected (see below), which doesn't
change actual call cost or response time, only which answers count as
correct.

Local model: Qwen2.5-Coder-7B via Ollama, RTX 3050 (6GB VRAM). Hosted
model: gpt-4o-mini via AvalAI (OpenAI-compatible gateway, pricing matches
official OpenAI rates). Single runs; retry temperature (0.4) makes
results non-deterministic on close cases — read as accuracy ± some
variance (see `FAILURE_TAXONOMY.md` §6).

## What the numbers show

**Routing beats the dumb baseline consistently, on both models.** Local:
66%→70%. Hosted: 80%→81%. Tier 3 (three-and-more-table joins) shows the
clearest, most consistent gain from the agent architecture across both
models — local +20pp, hosted +0pp this round but was the target of two
concrete, validated interventions (explicit join-key hints, join-path
reasoning) that measurably fixed real Binder Errors during development.

**A significant mid-project correction is part of this story, not hidden
from it:** an early tolerance bug in the scoring harness (`abs_tol=1e-6`,
tighter than the ~0.005 gap a 2-decimal `ROUND()` in ground truth can
create against an unrounded-but-correct model answer) was silently
penalizing every architecture on aggregation-heavy questions (tier 4
specifically). Found by digging into *why* tier 4 was unexpectedly weak
everywhere rather than accepting it, confirmed with a concrete example
(ground truth 4.16 vs. model's unrounded 4.155716524320005), and fixed.
Every reference run was re-graded under the corrected scorer before being
reported here — tier 4 improved 16-20pp across every architecture, and
one earlier finding (hosted routing appeared to slightly *hurt* accuracy)
turned out to be entirely a scorer artifact and was reversed once fixed.

**Cost and latency remain a real, practical tradeoff independent of the
correction.** Hosted inference cost about a nickel total for a full
100-question run, at roughly 1-6 seconds per query. Local inference is
free but 15-20x slower per query on this hardware (RTX 3050, 6GB VRAM) —
a genuine deployment consideration distinct from which architecture
scores higher.

Full failure-mode breakdown: see `FAILURE_TAXONOMY.md`.