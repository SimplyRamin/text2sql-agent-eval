# Phase 6 Plan: Routing + Specialist Paths

## Context

Phase 5 closed at 58/100 vs baseline's 59/100 (`DECISIONS.md`, 2026-08-31). The
tier breakdown showed the agent design working exactly where it targeted
(T3 +8pp, 3+ table joins) while regressing on T2 (-12pp) for reasons already
diagnosed as model-quality gaps that retries can't fix (case sensitivity,
unrequested filters) — not a retrieval or retry-architecture problem, per the
Phase 5 log and confirmed by direct inspection of q011.

Phase 6 ("routing + specialist paths") is underspecified in `PROJECT_BRIEF.md`
by design — it's chat's job to interpret it against real evidence rather than
default to a generic multi-agent pattern. This plan derives the interpretation
directly from re-reading the actual Phase 5 result CSVs
(`results/agent_qwen2.5-coder-7b_20260831_161251.csv` vs
`results/baseline_qwen2.5-coder-7b_20260825_154930.csv`), not just the
DECISIONS.md summary of them, and grounds every design choice in specific
question IDs.

## Evidence: three distinct failure clusters, re-derived from the reference CSVs

**1. Alias/join-path confusion on 3+-table joins — survives full retry budget.**
q040, q050, q057 all end in Binder Errors after `retry_count=2` (i.e. 3
attempts, temperature=0.4 exploration on retries 2 and 3) — e.g. q040 tries
`op.customer_id` where `op` is aliased to `order_payments`, which has no
`customer_id` column (it joins to `orders` via `order_id`, and `orders` joins
to `customers` via `customer_id` — a two-hop path the model collapses into
one). This is exactly the "Binder Errors from alias confusion on 3+ table
joins" pattern named in DECISIONS.md's T3 discussion, and it's important that
error-feedback retries (the mechanism Phase 5 relies on) do **not** reliably
fix it — the error message states what's wrong but not what the correct join
path is, so resampling at temp=0.4 doesn't converge.

**2. Fan-out/dedup errors on multi-child joins — silent, no error signal.**
q028 (T2), q048/q052/q054/q059 (T3) all join two or more one-to-many child
tables to the same parent (`orders` + `order_payments` + `order_reviews`, or
similar) without deduplication, e.g. q028's generated SQL uses `COUNT(*)`
where ground truth uses `COUNT(DISTINCT o.order_id)` — the exact fan-out bug
class DECISIONS.md already documented as a **ground-truth** authoring risk
(the q054 entry, 2026-08-22). Here the *agent* commits the same bug in
generated SQL. This class produces no execution error (the query runs fine,
just returns a wrong number), so it's invisible to the current retry loop's
error-feedback mechanism entirely — the model gets no signal at all that
anything is wrong.

**3. `category_translation` over-join — a real, distinct T2 regression cause.**
q011/q016/q028/q081 are named in DECISIONS.md as "confirmed to have fully
correct retrieved schema, model-quality issues" — but re-checking q016 and
q029 (this run's actual T2 regressions, not q081, which is T4 and belongs to
a different run given known retry-temperature non-determinism) shows a
concrete, fixable pattern: the question's category name (`informatica_acessorios`)
is already the *raw* `products.product_category_name` value, but the agent
joins `category_translation` and filters on `product_category_name_english`
instead — because `retrieve_tables()`'s `("products", "category_translation")`
keyword group always retrieves both tables together, and nothing tells the
model that the raw name is already what most questions want. Baseline (no
retrieval, sees only the schema it's given directly in that one prompt) didn't
hit this because it happened to phrase queries against the raw column; the
agent's retrieval-driven prompt made the wrong join *more* available, not less.
This is a schema-presentation problem, not a retry problem, and is separable
from cluster 1.

Only q011 (unrequested filter, wrong string case) is the case DECISIONS.md
already correctly diagnosed as unfixable by architecture — nothing in the
schema tells the model the DB's case convention. **Phase 6 does not attempt to
fix this class** (see Non-goals).

## Router design

**Signal: number of distinct entity-groups in `retrieved_tables`, not the
question's tier label.**

The tier is eval-only metadata. A real deployed system would not have it
available at inference time, so routing on it would make the router
untestable outside this harness — the router has to work off something the
agent actually sees.

`src/graph/retrieval.py`'s `KEYWORD_TABLES` already partitions the 12
physical tables into 8 conceptual entity groups (`orders`+`stg_orders`
travel together, `products`+`category_translation` travel together, etc.).
This is the right unit to count complexity on — not raw table count, which
double-counts paired tables and would make a two-entity question like
`orders`+`customers` look artificially bigger than it conceptually is.

Add `count_entity_groups(retrieved_tables: list[str]) -> int` to
`src/graph/retrieval.py`: counts how many `KEYWORD_TABLES` tuples have
non-empty intersection with `retrieved_tables`.

Verified against the reference run: T3 questions cluster at 3-4 groups
(q036=3, q043=4), T1/T2 mostly sit at 1-2 groups (q011=2), and a handful of
T4 aggregation-over-3-tables questions also hit 3 groups (q061=3) — which is
a feature, not noise: those T4 questions share the same join-path risk and
should get the same specialist treatment even though they're not labeled T3.

**Route: `"join"` if `count_entity_groups(retrieved_tables) >= 3`, else
`"simple"`.** On retries, `retrieve_schema` already falls back to the full
12-table `TABLES` list (all 8 groups) — so retries will always route to
`"join"` regardless of the original route. This is intentional, not a
special case to code around: a retry is inherently a higher-risk context
(first attempt already failed), and the more defensive prompt is the
reasonable default there.

**Rejected alternatives** (for the record, since the brief asked for
justification, not just a pick):
- *LLM-as-router* (a classifier call): adds a real LLM call's latency/cost to
  every question for a decision the retrieval step's output already answers
  for free. Not justified by evidence.
- *Local-vs-hosted routing by difficulty*: out of phase scope.
  `PROJECT_BRIEF.md`'s build order reserves hosted calls for Phase 7
  specifically, and the standing rule is "never make a hosted API call
  without asking first" — Phase 6 stays local-only, same as Phases 0-6 per
  the brief's phase table.

## Specialist prompt design

New module `src/graph/prompts.py` holds all Phase-6 prompt content (keeps
`src/baseline.py`'s `build_prompt`/`build_schema_string`/`extract_sql`
untouched and reused as-is by the `"simple"` route, per "don't duplicate
logic already in baseline.py").

**`FK_HINTS`** — a small static dict of the real join keys in this schema
(12 tables, already fully characterized in `DECISIONS.md`'s schema-scope
entry), e.g. `("order_payments", "orders"): "order_payments.order_id =
orders.order_id"`. `build_fk_hint_block(tables)` renders only the hints
relevant to the retrieved tables. This directly targets cluster 1: it makes
the two-hop `order_payments -> orders -> customers` path explicit instead of
requiring the model to infer it from column-naming convention.

**Dedup checklist** — one fixed instruction block, always included on the
`"join"` route (not conditionally triggered per-query — the router's `>= 3`
threshold already scopes it to the risk zone): *"If this query joins more
than one table that has a many-to-one relationship with the same parent
table (e.g. both `order_payments` and `order_reviews` joined to `orders`),
use `COUNT(DISTINCT ...)` or a deduplicating subquery — a plain `COUNT(*)` or
un-deduplicated `AVG`/`SUM` will double-count rows."* Targets cluster 2
directly.

**`build_join_prompt(schema, question, retrieved_tables)`** — schema + FK
hint block + dedup checklist + an instruction to write out the join path
(table → alias → join column, hop by hop) before the final query, in a
fenced sql code block. `extract_sql()` already prefers fenced blocks over
raw text (`src/baseline.py:59-73`), so this reasoning preamble doesn't need
any change to extraction.

There is also a retry variant, `build_join_retry_prompt(schema, question,
previous_sql, error, retrieved_tables)`. It is the retry analogue of
`build_join_prompt` and keeps the same FK-hint/dedup scaffolding rather than
reverting to the plain baseline-style retry prompt on later attempts — the
join-route question still needs that structure on attempt 2 and 3, not just
attempt 1.

**Universal category-name note.**

This one is NOT gated by route. Cluster 3 occurs at only 2 entity-groups
(`order_items` + `products/category_translation`), so the `>=3` router would
never catch it — it needs its own trigger. The rule: whenever
`category_translation` is present in `retrieved_tables`, append one fixed
clarifying line to *either* prompt variant (simple or join): *"`products.product_category_name`
already holds the category name used in this warehouse (e.g.
`informatica_acessorios`). Only join `category_translation` and filter on
`product_category_name_english` if the question explicitly asks for an
English/translated category name."* This is a schema-presentation fix, not a
routing decision, and is cheap to always include when relevant.

## Graph topology

Modify `src/graph/graph.py`'s `build_graph()` (or a new `build_routed_graph()`
— see Open questions below):

```
START -> retrieve_schema -> classify_complexity
classify_complexity --("simple")--> generate_sql_simple --> execute_and_score
classify_complexity --("join")-----> generate_sql_join   --> execute_and_score
execute_and_score --(route_after_score: retry)--> retrieve_schema
execute_and_score --(route_after_score: done)---> END
```

`classify_complexity` is a real node (not folded into a conditional-edge
lambda) so its decision is recorded in state as `route` and shows up in the
results CSV — needed for the Phase 6 write-up's route-level breakdown, and
matches this project's existing pattern of using LangGraph's actual
conditional-edge mechanism (this phase is explicitly the vehicle for
practicing that pattern per `PROJECT_BRIEF.md` §4) rather than hiding the
choice inside one node's control flow.

`src/graph/nodes.py` additions:
- `classify_complexity(state) -> {"route": ...}` using
  `retrieval.count_entity_groups`.
- `generate_sql_simple(state)` — today's `generate_sql` logic, unchanged,
  plus the universal category-name note appended when applicable.
- `generate_sql_join(state)` — uses `prompts.build_join_prompt` /
  `build_join_retry_prompt`.
- Both call a shared `_call_llm_and_record(state, prompt, temperature) ->
  dict` helper (new) that wraps `llm.complete()`, extracts SQL, and returns
  the state-update dict including the accumulated usage fields below — one
  place, reused by both variants, so cost/latency accumulation logic isn't
  duplicated between the two generate nodes.

`src/graph/state.py` additions to `GraphState`: `route: str`,
`total_cost: float`, `total_in_tokens: int`, `total_out_tokens: int`,
`total_llm_latency_ms: float` — all accumulated (read-current, add, return
new total) inside `_call_llm_and_record`, since plain `TypedDict` state has
no reducer and LangGraph node returns overwrite rather than merge/sum.

## Cost + latency instrumentation

Single timing primitive, added once, reused everywhere:

**`src/llm.py`** — wrap the existing `litellm.completion(...)` call in both
the `local` and `hosted` branches of `complete()` with
`time.perf_counter()`, add `"latency_ms"` to the `result` dict before it's
cached/returned. On a cache hit, the stored `latency_ms` is the *original*
generation's latency (a real, meaningful number — how long that response
actually took to produce) — no separate cache-read timer needed, since
`cached: True` already lets any consumer filter cache hits out when
computing "typical fresh-call latency" stats. This is the only change needed
to `llm.py`, and it's the sole call site both `baseline.py` and
`graph/nodes.py` already go through, so nothing downstream duplicates it.

**Local-run reality check**: `PRICING` is empty and local calls always cost
`$0.0` (`src/llm.py:61`), so `cost` will be all-zeros for every Phase 6 run —
correct and expected, not a bug to chase. The locally-meaningful proxy for
"cost" is **token count** (`in_tokens`/`out_tokens`, already returned by
`complete()`'s `usage` dict but currently discarded by both `baseline.py`
and `graph/run.py`) — this is what actually differs between the `"simple"`
and `"join"` routes (the join prompt is longer) and is worth recording now
so Phase 7's real dollar-cost comparison has a local baseline to sanity-check
against.

**Per-question wall-clock**: added at the two entry-point loops, not inside
`llm.py` or the graph nodes — this captures total time including retrieval,
scoring, and (for the join route) the extra prompt-building overhead, which
`total_llm_latency_ms` alone would miss:
- `src/graph/run.py`'s `run_agent()`: wrap each `graph.invoke(initial_state)`
  call with `time.perf_counter()`.
- `src/baseline.py`'s `run_baseline()`: wrap each `llm.complete(...)` +
  `score_question(...)` pair the same way.

This is genuinely new logic at exactly two places (both loops already exist
and already iterate per-question) — not a duplication of anything, since
baseline and the agent never shared a per-question timing wrapper before.

**Retroactively instrumenting `baseline.py` too** (not just the new routed
path) is deliberate: it makes the eventual 3-way comparison (baseline vs
Phase 5 agent vs Phase 6 routed) apples-to-apples on cost/latency, which the
brief's Phase 4/5 numbers never captured (`README.md`/`PROJECT_BRIEF.md`
Phase 4 requirement was accuracy-only; Phase 6 is explicitly the phase that
adds cost+latency as required metrics).

## Results schema changes

`write_csv()` in both `src/baseline.py` and `src/graph/run.py` gains columns:
`cost`, `in_tokens`, `out_tokens`, `llm_latency_ms`, `wall_clock_ms` — plus
`route` in `graph/run.py`'s version only (baseline has no router).
`print_summary()` (already shared — `graph/run.py` imports it from
`baseline.py`) gains a few lines reporting mean/median wall-clock and total
tokens, so the numbers are visible in console output without opening the
CSV.

Output file naming: routed runs write to
`results/routed_<model>_<timestamp>.csv`, keeping `agent_...` and
`baseline_...` prefixes meaning what they already mean (existing committed
CSVs stay valid references, nothing is renamed retroactively).

## Evaluation plan

Re-run the full 100-question set once routing is implemented and hand-typed
(`uv run python -m src.graph.run --routed`, see Open questions on CLI
shape). Compare against the two committed reference runs
(`results/baseline_qwen2.5-coder-7b_20260825_154930.csv`,
`results/agent_qwen2.5-coder-7b_20260831_161251.csv`) on:
- Overall + tier breakdown, same format as `print_summary()` today.
- New route-level breakdown (`"simple"` vs `"join"` accuracy) — this is the
  number that tells you whether the specialist prompt actually helps within
  the population it targets, separate from tier, which is eval-only metadata.
- Targeted before/after on the three clusters, by question ID: q040/q050/q057
  (cluster 1 — did the join-path scaffold fix the Binder Errors that survived
  retries in Phase 5?), q028/q048/q052/q054/q059 (cluster 2 — did the dedup
  checklist stop the fan-out overcounting?), q016/q029 (cluster 3 — did the
  category note stop the wrong-column join?).
- Token-count delta between routes, as the local proxy for what Phase 7's
  dollar cost comparison will show.

Same caveat Phase 5's log already states applies here too: retry
temperature=0.4 bypasses the cache and is genuinely non-deterministic
run-to-run on close cases — a single routed run's numbers should be read
with that variance in mind, not treated as exact, consistent with how Phase
5's q029 flip was already characterized.

Whatever the routed run shows, write the result to `DECISIONS.md` the same
way every other phase result was — hand-typed by the user, not by Claude
Code, per the standing 2026-08-05 decision that Claude Code stays plan-mode-only
and all implementation (now explicitly including Phase 6, since
`PROJECT_BRIEF.md` §5 marks Phase 6 as "you write nodes") is hand-typed.

## Non-goals (explicitly out of scope for Phase 6)

- **Fixing q011-class semantic errors** (unrequested filters, wrong string
  case). DECISIONS.md already concluded these are genuine model-knowledge
  gaps, not something retrieval/retry/routing can fix, and explicitly said
  "not pursuing further tuning" for this class. Phase 6 doesn't relitigate
  that; a router/specialist-prompt design has no lever over a fact the model
  just doesn't know (DB string casing convention).
- **Local-vs-hosted routing.** Reserved for Phase 7 per the brief's phase
  table; mixing it into Phase 6 would also require a hosted API call before
  the user has approved one for this phase.
- **An LLM-based router/classifier.** Rejected above — the retrieval step
  already produces a free, sufficient signal.

## Open questions before implementation

1. **CLI shape**: extend `src/graph/run.py` with a `--routed` flag that
   swaps which graph-builder function is used (reuses all of
   `run_agent()`'s loop/CSV/summary code as-is — recommended, since Phase 5's
   `GraphState` additions apply equally whether routed or not, and a
   non-routed run just gets an empty `route` column, which is a harmless
   bonus: re-running today's plain agent afterward would give it cost/latency
   columns too, for free) — vs. a separate `src/graph/run_routed.py`
   mirroring the Phase 4/5 one-script-per-phase convention. Recommend the
   flag; flagging the alternative in case the phase-per-file symmetry matters
   more to you for the write-up's narrative.
2. **Router threshold** (`>= 3` entity groups): validated against this run's
   CSV distribution above, but worth eyeballing against the full 100 once
   `count_entity_groups` exists, in case the boundary should be adjusted
   before committing to a full run.
