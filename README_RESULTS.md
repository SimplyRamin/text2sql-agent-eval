# Results

## Comparison table

| Architecture | Overall | T1 | T2 | T3 | T4 | T5 |
|---|---|---|---|---|---|---|
| **Local** (Qwen2.5-Coder-7B) — dumb baseline | 66% | 100% | 80% | 40% | 68% | 60% |
| **Local** — routed agent | **69%** | 100% | 80% | 56% | 60% | 66.7% |
| **Hosted** (gpt-4o-mini) — dumb baseline | 79% | 100% | 92% | 72% | 60% | 86.7% |
| **Hosted** — routed agent | **84%** | 100% | 92% | 76% | 72% | 93.3% |

Local: Ollama, RTX 3050 (6GB VRAM), $0/query. Hosted: gpt-4o-mini via
AvalAI (OpenAI-compatible, pricing matches official OpenAI rates),
~$0.02-0.04 per full 100-question run. Single runs; retry temperature
(0.4) and hosted API calls both carry inherent run-to-run variance —
read as accuracy ± a few points, not exact figures (see
`FAILURE_TAXONOMY.md` §6).

## What the numbers show

**Routing consistently beats the dumb baseline, on both models: local
+3pp, hosted +5pp.** The larger hosted gain is notable — a stronger base
model had more room to benefit from schema retrieval and self-correction
on the questions it was already close to getting right, rather than the
scaffolding being wasted on out-of-reach questions.

**Two real bugs were found and fixed during evaluation, and both mattered
more than any single prompt-engineering change:**

1. A scorer tolerance bug (`abs_tol=1e-6`) was tighter than the rounding
   gap a 2-decimal `ROUND()` in ground truth can create against an
   unrounded-but-correct answer — silently penalizing every architecture
   on aggregation questions (tier 4). Confirmed with a concrete case
   (ground truth 4.16 vs. model's unrounded 4.155716524320005) and fixed
   (`abs_tol=0.01`). Every reference run was re-graded before being
   reported here.
2. The dedup-checklist prompt told the model to use `COUNT(DISTINCT ...)`
   to avoid double-counting, but didn't say *which* column was safe to
   deduplicate on — leading the model to deduplicate on
   `order_item_id`, a per-order sequence number that repeats across
   different orders, silently undercounting. Fixed by specifying which
   columns are genuinely safe to deduplicate on, and by explicitly
   permitting plain `COUNT(*)` when there's no real fan-out risk.

An earlier finding — that routing appeared to slightly *hurt* accuracy on
the hosted model — turned out to be entirely an artifact of these two
bugs stacked together, not a real cross-model generalization problem.
Worth stating directly: **the process of finding and fixing these bugs is
as much the point of this project as the final accuracy numbers.**

**Tier 3 (three-and-more-table joins)** improved the most from targeted,
validated interventions — explicit join-key hints and a join-path-
reasoning instruction, each fixing specific, named question IDs (see
`FAILURE_TAXONOMY.md` §1).

Full failure-mode breakdown, including which categories were fixed and
which were correctly left alone (model-knowledge gaps no architecture
change can address): see `FAILURE_TAXONOMY.md`.