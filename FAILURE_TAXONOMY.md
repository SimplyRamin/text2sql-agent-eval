# Failure Taxonomy — text2sql-agent-eval

Synthesized from DECISIONS.md across Phases 4-7. Six failure categories,
each with concrete question IDs and which architectures were/weren't able
to address them.

---

## 1. Join-path / alias confusion (3+-table joins)

**Symptom:** Binder Errors where the model references a column on the
wrong table, or collapses a two-hop join into one step.

**Examples:** q040 (Phase 5: `op.customer_id` — order_payments has no
direct customer_id, needs orders as bridge), q050, q057.

**What helped:** Schema retrieval with capped retries (Phase 5), then Phase 6's `FK_HINTS`
and explicit join-path-reasoning instruction, targeted this class directly. On the local
model, tier 3 went from 40% (single-call baseline) to 56% (routed agent), graded with the
corrected scorer; on the hosted model it moved from 72% to 76%. Intermediate Phase 5
figures were graded under the earlier, too-strict scorer and were not re-run, so they are
not quoted here.

**What didn't fully close it:** Even with FK_HINTS, some 3+-table
questions still fail after full retry budget — the hint block only
covers pairwise joins actually present in `FK_HINTS`, and doesn't
prevent the model from inventing an unneeded join in the first place
(see category 4).

---

## 2. Fan-out / deduplication errors (silent, no error signal)

**Symptom:** Query executes successfully but returns a wrong number —
joining 2+ one-to-many child tables to the same parent without
deduplication (e.g. `order_payments` + `order_reviews` both joined to
`orders`) inflates COUNT/AVG.

**Examples:** q028 (agent used COUNT(*) where DISTINCT was needed),
q048/q052/q054/q059. Notably, this same bug class was first caught in
*ground truth* itself (original q054, Phase 2/3) before it was ever seen
in generated SQL — the project's own eval questions weren't immune to it
either.

**What helped:** Phase 6's dedup checklist, targeted directly at this
class. One refinement needed mid-build: the checklist told the model
*what* to do (COUNT(DISTINCT...)) but not to qualify the column name,
which caused a new bug (q086, q090 — ambiguous column reference across
multiple joined tables sharing a column name) until the checklist was
updated to require qualification.

**Known side effect:** The checklist can over-trigger — q013 got an
unnecessary `COUNT(DISTINCT...)` on a query with zero fan-out risk (a
single, safe join). Not fixed — narrow, low-cost false positive compared
to the real bug it prevents.

---

## 3. Schema-presentation-induced errors (retrieval creates the problem)

**Symptom:** The agent's own retrieval step makes an error *more* likely
than baseline's full-schema approach, by narrowing the model's context in
a way that surfaces the wrong table pairing as the obvious choice.

**Example:** q016 — `category_translation` always retrieved alongside
`products` (structurally paired in the keyword table), which made the
translated-category join look like the default even when the question's
category name was already the raw, untranslated value. Baseline didn't
hit this specific failure because full-schema presentation didn't bias
toward either join.

**What helped:** Phase 6's ungated category-name note (added regardless
of route, whenever `category_translation` is retrieved) — confirmed
fixed directly (q016 passed on first attempt in the `--limit 20` dry-run
that validated it).

**Broader pattern worth naming:** this is the only failure class where
the *agent architecture itself* was the cause, not the model's reasoning
— a caution that schema retrieval, while generally net-positive, can
introduce new failure modes not present in the naive baseline.

---

## 4. Self-inflicted over-complication

**Symptom:** The model adds an unnecessary join, subquery, or filter that
the ground truth doesn't need, then gets confused by its own addition.

**Examples:** q019 (added an unneeded third join to `orders`, then
miscounted grain — DISTINCT on the wrong column), q064 (introduced a
subquery aliased `r`, then referenced a column that subquery never
selected), q077 (hosted run: `Referenced table "op" not found! Candidate
tables: "subquery"` — same shape, on a different model).

**Note on a since-corrected finding:** an initial hosted run appeared to
show routing slightly *hurting* accuracy (70% vs 71% baseline). This
turned out to be caused by two compounding bugs, not a real cross-model
generalization problem: a scorer tolerance bug penalizing correctly-
rounded answers (see DECISIONS.md, 2026-09-29), and a dedup-checklist
gap that caused the routed agent to deduplicate on a non-unique column
(order_item_id) on two tier-2 questions it should have easily passed.
After both fixes, routing improves accuracy on both local (+3pp) and
hosted (+5pp) models, consistently. q021/q025 remain real, standalone
examples of this failure category (unnecessary structural complexity),
but do not represent an aggregate cross-model trend.

**Not fixed:** No prompt change was made for this class. Fixing it would
mean walking back the reasoning instruction that's also directly
responsible for category-1 gains — a real tradeoff, not investigated
further within this project's scope.

---

## 5. Model-knowledge gaps (unfixable by this project's architecture choices)

**Symptom:** Syntactically and structurally correct SQL that answers a
*different* question than the one asked — wrong assumptions about data
conventions the model has no way to know from the schema alone.

**Examples:**
- q011: added an unrequested `customer_city` filter, and used the wrong
  case (`'Rio de Janeiro'` vs. the warehouse's actual lowercase storage).
- q086: added an unrequested `order_status IN (...)` filter that omits
  `'canceled'`, directly contradicting the question's explicit instruction
  to include canceled orders.

**What was tried and didn't work:** Phase 5's retry-temperature increase
(0.4 on retries, to let resampling explore a different answer) was
specifically tested against q011 and confirmed *not* to fix this class —
resampling changes the SQL's surface form but not the model's underlying
wrong assumption, since nothing in the prompt corrects it.

**Deliberately out of scope:** DECISIONS.md concluded early (Phase 5)
that no retrieval, retry, or routing design has a lever over a fact the
model simply doesn't know (e.g. DB string-casing convention) — correctly
distinguished from categories 1-4, which *are* architecture-addressable.

---

## 6. Non-determinism / evaluation-harness robustness

**Symptom:** Not a model failure — the *evaluation itself* could have
silently produced misleading numbers.

**Examples:**
- q069 ground truth: `ORDER BY` with no tiebreaker on a `LIMIT`-bounded
  query, caught by the scorer's own self-comparison check (ground truth
  scored against itself, should be 100%, wasn't).
- The disk cache bypassing non-zero temperature (Phase 5): a "random"
  retry was accidentally deterministic because the cache replayed the
  first sampled response forever, until the cache was made
  temperature-aware.
- Retry temperature=0.4 is *inherently* non-deterministic run-to-run on
  close cases (q029 flipped PASS→FAIL between two otherwise-identical
  runs) — an accepted property of the design, not a bug, but means any
  single run's accuracy number carries some real variance.

**Why this category matters for the write-up:** every result in this
project should be read as "accuracy ± some variance," not an exact
figure — worth stating explicitly rather than presenting single-run
numbers as if they were precise.

---

## Summary: which architecture change addressed which category

| Category | Baseline | +Retrieval/Retry (Phase 5) | +Routing (Phase 6) |
|---|---|---|---|
| 1. Join-path confusion | ✗ | partial | ✓ (largest single improvement) |
| 2. Fan-out/dedup | ✗ | ✗ (no error signal to retry on) | ✓ (dedup checklist) |
| 3. Schema-presentation-induced | n/a (doesn't retrieve) | introduced | ✓ (category note) |
| 4. Self-inflicted complexity | rare | rare | introduced (tradeoff w/ #1's fix) |
| 5. Model-knowledge gaps | ✗ | ✗ | ✗ (correctly out of scope) |
| 6. Harness non-determinism | n/a | found & partially fixed | ongoing caveat |