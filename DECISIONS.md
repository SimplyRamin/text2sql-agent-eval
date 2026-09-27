# DECISIONS.md

This is the bridge between chat (design/decisions) and Claude Code (construction).
Every time a design call gets made in chat, it gets written here and committed.
Claude Code reads this file at the start of every session — that's how it learns
what chat decided without any shared memory between the two.

Format: newest entries at the top. One entry per decision. Include the *why*,
not just the *what* — the reasoning is what Claude Code needs to apply it
consistently, and what you'll need in an interview six months from now.

---

## Log

### 2026-09-27 — tiktoken cache persistence fixed; offline fallback added
Decision: root cause of the earlier VPN-then-fails-again issue was
tiktoken defaulting to the system temp directory for its cache, which
wasn't persisting between runs on this machine. Fixed by pinning
TIKTOKEN_CACHE_DIR to a stable project-local .tiktoken_cache/ folder
(gitignored) via os.environ.setdefault in dry_run.py. Also added a
genuine offline fallback in count_tokens (character-count heuristic,
~4 chars/token, deliberately biased toward overestimating) so --dry-run
never hard-fails on a network hiccup — consistent with this module's
purpose as the always-available safety check before spending money.
Confirmed fixed: count_tokens('...', 'gpt-4o-mini') now returns the real
tiktoken count (6) without VPN, using the persisted local cache.
Status: resolved. .tiktoken_cache/ added to .gitignore.

### 2026-09-02 — q086 root cause confirmed: unrequested status filter contradicts explicit question wording
Decision: q086 ground truth is a plain SELECT COUNT(*) FROM orders (no
filter). The model added WHERE order_status IN ('created', 'processing',
'shipped', 'delivered', 'unavailable') — a filter never requested, and
one that appears to omit 'canceled' despite the question explicitly
stating canceled orders must be included ("including ones that were
never delivered or were canceled"). This is the same failure family as
Phase 4 baseline's q020 (over-engineering: adding logic the question
didn't ask for) and distinct from the join/dedup/qualification bugs
found and fixed earlier today.
Status: not fixed — same category as q011's case-sensitivity gap,
a model-knowledge/instruction-following issue no prompt scaffolding
change was targeted at. Noted for Phase 8's failure taxonomy.

### 2026-09-02 — Phase 6 complete: 63/100, best result across all three phases
Decision: Phase 6 routed agent (schema retrieval + capped self-correction +
complexity-based routing to specialist join prompts) scored 63/100 after
the dedup-checklist column-qualification fix. Confirmed q086/q090's
"Ambiguous reference" Binder Errors are gone — the model now avoids the
ambiguity by restructuring the query (dropping unneeded joins / using
GROUP BY) rather than needing an explicit qualification; both still fail,
but for different, unremarkable reasons, not the bug that was fixed.
Full comparison vs baseline (59%) and Phase 5 (58%):
T1 100/100/100 (=), T2 76/64/76 (baseline parity, +12pp vs Phase 5),
T3 32/40/52 (+20pp vs baseline, +12pp vs Phase 5 — the design's original
target, now the clearest success across all three phases), T4 52/52/44
(-8pp vs both, stable across two Phase 6 runs — a real, persistent
regression not yet root-caused), T5 60/60/66.7 (+6.7pp vs both).
Overall: 63% vs baseline 59% and Phase 5 58% — first clean win across
the board, not just on the targeted tier.
Known open item, not investigated further now: tier 4 regression is
consistent and unexplained. Worth a targeted look in Phase 8's failure
taxonomy, alongside the q013-style "unnecessary DISTINCT on a safe query"
pattern noted earlier, which was not further chased today.
Status: Phase 6 closed. results/agent_qwen2.5-coder-7b_20260902_120509.csv
committed as the reference run.

### 2026-09-02 — Phase 6 full run: 60/100, tier 3 +20pp vs baseline, tier 4/5 regressed
Decision: Phase 6 routed agent scored 60/100 vs baseline 59% and Phase 5's
58%. Tier 3 (the design's original target) improved to 52% — +20pp vs
baseline, +12pp vs Phase 5 alone. Tier 4 (44%, -8pp vs Phase 5) and tier 5
(53.3%, -6.7pp) regressed, both traced to the "join" route specifically.
Root cause 1 (q086, q090): the dedup checklist correctly prompts
COUNT(DISTINCT ...) but didn't require column qualification — with
multiple joined tables sharing a column name (order_id in both orders and
order_payments), an unqualified COUNT(DISTINCT order_id) is genuinely
ambiguous SQL. Fixed by adding an explicit qualification instruction to
DEDUP_CHECKLIST.
Root cause 2 (q064): the join-path-reasoning instruction appears to have
pushed the model toward overcomplicating a query with an unnecessary
subquery, which then had its own column-scoping bug (referenced a column
never selected by the subquery). Not fixed — noted as a real, harder-to-
prevent side effect of encouraging explicit reasoning: it can also
encourage unnecessary structural complexity. No prompt change made for
this one; would need more evidence before altering the reasoning
instruction, since it's also directly responsible for tier 3's gains.
Why not revert the dedup checklist instead of patching it: q016 (cluster
3) and multiple tier-3 gains are directly attributable to Phase 6's
prompt interventions working correctly; the qualification gap is a
precise, narrow fix rather than a sign the whole approach is wrong.
Status: dedup checklist fixed. Re-running full 100 to confirm q086/q090
resolve and tier 4/5 partially recover, before treating any number as
final.

### 2026-09-02 — Phase 6 --limit 20 dry-run: real findings, not just pass/fail
Decision: q016 (cluster 3, category_translation over-join) now passes —
confirms the ungated category-name note works as designed. Of 3 join-route
failures (q011/q013/q019): q011 is the already-known non-join model-
knowledge gap (case sensitivity), correctly routed to "join" by entity-
group count but its actual failure is unrelated to joins. q013 and q019
are new findings: q013's join is fully correct but the model added an
unnecessary COUNT(DISTINCT ...) where plain COUNT(*) was right — likely
the dedup checklist being applied defensively even on single-join,
no-fan-out-risk queries. q019 added an unneeded third join (orders) not
present in ground truth, then miscounted grain (COUNT(DISTINCT order_id)
instead of COUNT(DISTINCT product_id)) — a self-inflicted join-path error
FK_HINTS didn't prevent, since the extra join wasn't necessary at all.
Why this matters: the dedup checklist may have a false-positive cost
(over-applying DISTINCT on safe queries) that wasn't visible in the
original 3-cluster analysis, since that analysis only looked at cases
where dedup was actually needed and missing. Worth watching in the full
100-question run whether this pattern recurs, before concluding whether
the checklist's benefit (fixing real fan-out) outweighs this cost.
Status: noted from --limit 20. Proceeding to full 100-question run to see
if this is a real pattern or isolated to these two questions.

### 2026-09-02 — wall_clock_ms includes cache hits; note for reporting
Decision: no code change — documenting a real interpretive caveat.
wall_clock_ms measures actual elapsed time per question this run,
including cache hits (near-instant) for temperature=0 first-attempts that
match a previous run's cached prompt. This is correct behavior, not a
bug — confirmed by re-running --limit 3 with a cleared cache: mean jumped
from 73ms (cached) to 4325ms (fresh calls).
Why this matters for interpretation, not code: the eventual Phase 6/7
latency comparison should either (a) always run against a cleared cache
when latency is the metric being reported, or (b) report cache hit rate
alongside wall-clock so a fast mean isn't misread as "the agent is fast"
when it's actually "most of this run was replayed from a previous run."
No decision needed now on which — just flagging so the full-100 run isn't
reported without this caveat attached.
Status: noted, no code change. Will clear cache before the real Phase 6
full-run comparison to get honest fresh-call latency numbers.

### 2026-09-02 — retrieve_tables missing orders as implicit join bridge
Decision: retrieve_tables() had no way to surface `orders`/`stg_orders`
for questions that mention customers and an order-child table (payments,
items, reviews) but never use an "order"-related word directly (e.g. q040:
"customers... paid using 'boleto'" — no word triggers the orders group,
even though customers->orders->order_payments is the only real join path).
Added _add_order_bridge(): if customers and any order-child table are both
retrieved but orders isn't, inject orders+stg_orders.
Why: found while validating Phase 6's routing signal (count_entity_groups)
against the full 100 questions, before writing any Phase 6 prompt code.
q040 is one of the three flagship cluster-1 examples Phase 6's FK_HINTS/
join-path-reasoning prompt is meant to fix — but no prompt design can work
around a schema that's missing the bridge table entirely. This is a
retrieval-completeness gap, structurally different from Phase 5's
underscore-boundary regex bug: it's about implicit join topology, not
keyword-matching precision.
Status: fixed. Must re-run the full retrieve_tables check against all 100
questions to confirm q040 (and any similar case) now includes orders, and
re-check count_entity_groups' >=3 distribution since some questions'
group counts will shift by +1.

### 2026-08-31 — Phase 6 open questions resolved
Decision: CLI shape is a --routed flag on src/graph/run.py (not a
separate script) — GraphState's new fields apply identically either way,
and it means re-running the plain Phase 5 agent also gets cost/latency
data for free. Router threshold (>=3 entity groups via
count_entity_groups) stays provisional until checked against the full
100-question distribution once the function exists — adjust only if that
check reveals real miscategorization, not preemptively.
Status: decided. Ready to implement once the plan reprint is clean.

### 2026-08-31 — Phase 5 complete: agent 58/100 vs baseline 59/100
Decision: LangGraph agent (schema retrieval + capped self-correction,
retry temperature=0.4) scored 58/100, both fixes applied (cache-bypass on
non-zero temperature; retrieval keyword underscore-boundary bug). Tier
breakdown: T1 100% (=), T2 64% (baseline 76%, -12pp), T3 40% (baseline
32%, +8pp), T4 52% (=), T5 60% (=).
Why roughly at parity overall: the agent clearly worked on the tier it
targeted — T3 (3+-table joins) improved the most, consistent with the
design intent (narrower schema reduces alias confusion; error-feedback
retries recover real Binder Errors, confirmed directly on q029/q040/q049
across runs). T2 regressed because baseline's always-full-schema
approach was, for two-table joins specifically, already sufficient —
narrowing never helps when nothing was missing, and can only add risk.
Of T2's 6 regressions, 4 (q011/q016/q028/q081) were confirmed via direct
inspection to have fully correct retrieved schema; their failures are
model reasoning errors (wrong filter, wrong case sensitivity) that
resampling at temperature=0.4 could not reliably fix, since nothing in
the prompt/schema tells the model what it doesn't know.
Also observed: retry temperature=0.4 makes results non-deterministic
run-to-run on close cases (q029 flipped PASS→FAIL between two runs with
identical code) — an inherent, expected property of trading determinism
for exploration on retries, not a bug. Single-run numbers should be
treated as having some variance around them, not as exact.
Status: Phase 5 closed. results/agent_qwen2.5-coder-7b_20260831_161251.csv
committed as the reference run. Not pursuing further tuning — the
tier-3 improvement and honestly-characterized tier-2 regression are a
more defensible finding than chasing a higher aggregate number.

### 2026-08-31 — retrieve_tables underscore boundary bug fixed
Decision: _keyword_matches used \bkeyword\b, which fails to match a keyword
that's a prefix of an underscored column-style word (e.g. "freight" does
not match inside "freight_value", since \b requires a boundary and "_" is
a word character in regex). Fixed to \bkeyword(\b|_) — matches on a normal
boundary OR immediately before an underscore.
Why: found via evidence, not inspection — q034 ("total freight_value
charged by sellers...") retrieved only ['sellers'], missing order_items
entirely, causing a real accuracy regression vs baseline. Confirmed fix
via before/after retrieve_tables() output on all 100 questions: 2 of the
6 known tier-2/4/5 regressions (q034, q096) had their retrieved-table set
change and gain a needed table; the other 4 regressions (q011, q016, q028,
q081) already had correct retrieval before this fix, confirming their
failures are unrelated to retrieval — model-quality issues instead (q011
already diagnosed: case-sensitivity + unrequested filter).
Status: fixed and verified against the full question set.

### 2026-08-31 — Phase 5 partial validation (--limit 40): fix helps, tier 2 still trails baseline
Decision: with the cache-bypass-on-nonzero-temperature fix confirmed
working, re-ran --limit 40. q029 recovered via retry (previously failed
all 3 attempts under the cache bug) — real evidence the temperature fix
works. Tier 2 improved 60%→64% but remains below baseline's 76% on the
same 25 questions. Tier 1 identical to baseline (100%). Tier 3 sample too
small (5 questions) to compare meaningfully yet.
Why the remaining gap is not being chased further right now: spot-checked
q011 specifically — the model's failure is a genuine knowledge gap (adds
an unrequested filter, wrong case for a string literal it can't know is
stored lowercase) that resampling can surface variety on but not reliably
fix, since nothing in the prompt/schema tells the model the actual
convention. This is a real, bounded limitation of schema-retrieval +
self-correction for semantically-wrong-but-valid SQL, distinct from its
clear effectiveness against execution errors (q029, q040). Worth stating
directly in Phase 8's failure taxonomy rather than further tuning
generate_sql for this specific case.
Status: fix validated. Proceeding to the full 100-question run as the
Phase 5 reference result, tier 2 regression included honestly.

### 2026-08-31 — Retry temperature fix confirmed working; q011 remains a case-sensitivity gap
Decision: with the cache fix from the prior entry applied and cache/ cleared,
confirmed real sampling now occurs on retries (temperature=0.4) — q011's
attempt 2/3 SQL genuinely differs from attempt 1, no longer a frozen replay.
q011 itself still fails after all 3 attempts: the model persistently adds a
redundant customer_city filter and capitalizes 'Rio de Janeiro', which
doesn't match the warehouse's lowercase-stored city values. Also observed:
temperature=0.0 output for the same prompt changed across separate runs
after a cache clear (dropped a column alias) — expected GPU non-determinism
in llama.cpp/cuBLAS kernels, not a code bug, worth remembering if any
future result looks "impossible" to reproduce exactly.
Why this matters: confirms two distinct self-correction failure modes.
Execution errors (q040's Binder Error) are recoverable — the model gets a
concrete, actionable signal. Semantically-wrong-but-valid queries (q011)
are much harder to recover via resampling alone, because nothing in the
prompt tells the model *what* it doesn't know (here: case-sensitivity
convention). This is a real, bounded limitation of this design, not a bug
to keep chasing — worth stating plainly in Phase 8's failure taxonomy.
Status: fix confirmed correct. No further changes to generate_sql's
retry logic planned for Phase 5.

### 2026-08-31 — Cache bypassed for non-zero temperature calls
Decision: src/llm.py's complete() now skips both cache_get and cache_set
when temperature != 0.0. Previously the disk cache (keyed on
model|temperature|prompt) applied unconditionally.
Why: discovered while debugging why Phase 5's retry loop (temperature=0.4
on retries, to let self-correction actually explore a different answer
after a wrong-but-valid-SQL failure) produced byte-identical SQL across
all 3 attempts on q011. Root cause: the cache's model|temperature|prompt
key assumes (model, temperature, prompt) is a pure function — true at
temperature=0, false at temperature=0.4, where repeat calls should
legitimately sample different completions. Once a temp=0.4 call was
cached once, every later call with the same prompt silently replayed
that one frozen sample forever, making "randomness" deterministic by
accident. This wasn't caught earlier because temperature=0 has been the
project-wide convention since Phase 0 — this is the first code path that
ever calls complete() with a non-zero temperature.
Status: fixed in llm.py. Must clear cache/ before re-testing to remove
already-poisoned entries from before the fix.

### 2026-08-25 — Phase 4 baseline complete: 59/100 (59%)
Decision: dumb single-call baseline (full schema in prompt, no retrieval,
no self-correction, temperature=0) scored 59/100 against qwen2.5-coder:7b
local. Tier breakdown: T1 10/10 (100%), T2 19/25 (76%), T3 8/25 (32%),
T4 13/25 (52%), T5 9/15 (60%). Fixed a real extract_sql() bug during
review (`!= 1` should have been `!= -1`, would have silently emptied any
SQL response without a trailing semicolon) before this run.
Why this number matters: it's the reference point Phase 5's LangGraph
agent (schema retrieval + capped self-correction) gets measured against.
Notable: T3 (multi-table joins) is the weakest tier, worse than T4
(aggregation) — several Binder Errors show the model losing track of
which alias maps to which table once 3+ tables are joined. Worth
revisiting in Phase 8's failure taxonomy, not investigated further now.
Status: Phase 4 closed. results/baseline_qwen2.5-coder-7b_<timestamp>.csv
committed as the permanent Phase 4 reference run.

### 2026-08-22 — q069 non-deterministic ORDER BY, scorer self-check caught it
Decision: q069 (ordered: true, ORDER BY order_count DESC LIMIT 5) had no
tiebreaker. Empirically confirmed non-determinism: two identical executions
returned the same 5 customers but with two order_count=7 ties swapped in
position. Fixed with a secondary sort key (ORDER BY order_count DESC,
c.customer_unique_id ASC), reverified deterministic across 3 runs. Scanned
all 15 other ordered:true questions; 12 had ORDER BY+LIMIT worth checking,
3 were structurally safe by construction (sort key unique by GROUP BY or
filter scope) and skipped with reasoning. All 12 checked had zero tied
sort-key values several rows past their cutoffs, confirmed empirically
(run twice, byte-identical) rather than trusting the deduction alone.
Why: caught by scorer.score_question run against ground-truth SQL as its
own "agent answer" for all 100 questions — should be 100% by construction.
Non-deterministic ground truth can't be reliably matched by any agent,
correct or not, and would have silently penalized every architecture
equally without ever looking suspicious in results.
Status: fixed. Full self-comparison harness passes 100/100 across 5
consecutive runs.

### 2026-08-22 — Fan-out bug scan: q054 fixed, q048/q060 confirmed safe as-is
Decision: scanned all 100 questions for the two-one-to-many-table JOIN shape
that caused the q054 bug (joining order_payments and order_reviews directly
to orders in the same query, without deduplication). Found 6 total instances:
q023, q041, q052 already used the safe dedup-subquery pattern; q054 was
fixed (see prior entry); q048 and q060 have the same raw double-JOIN shape
but use COUNT(DISTINCT order_id), not AVG. Empirically verified (not just
reasoned) that COUNT(DISTINCT order_id) is fanout-immune — as-written and
fully-deduplicated versions return identical values for both. Left
unchanged.
Why: COUNT(DISTINCT) already collapses duplicate rows by definition; AVG
has no equivalent protection, which is what made q054 a real bug and q048/
q060 not. Rewriting the latter two to match q054's subquery shape would add
defensive boilerplate without changing correctness — the differing SQL
shapes across similar-looking queries are deliberate and reflect which
aggregate is actually at risk, not an inconsistency.
Status: scan complete, no further changes to questions.yaml.

### 2026-08-22 — q054 fan-out bug caught in review, fixed
Decision: q054's ground-truth SQL joined order_payments and order_reviews
(both one-to-many with orders) without deduplication, inflating AVG for
orders with multiple qualifying payment rows. Fixed to filter distinct
qualifying order_ids first, then average against order_reviews directly —
same pattern already used correctly in q052.
Why: caught in manual review, not by execution (fan-out doesn't error, it
silently skews results) — worth remembering this class of bug specifically
evades the "did it execute" validation and needs an eyeball pass on any
query joining two one-to-many tables at once.
Status: fixed and re-validated.

### 2026-08-22 — data/olist.db sourced from olist-customer-intelligence, .gitignore fixed
Decision: copied data/olist.db (~59MB) from D:\Projects\olist-customer-intelligence
into this repo's data/ folder — this repo had no warehouse file yet. Verified
its table list matches the schema scope decided earlier, word-for-word,
including the excluded tables (customer_features, int_customer_orders,
product, order_payment) actually being present and correctly unused.
Also fixed .gitignore: it had *.duckdb but the file is olist.db (.db
extension, not .duckdb) — would NOT have been excluded and could've been
committed as a 59MB blob. Added data/*.db.
Why: evals/questions.yaml generation requires executing ground-truth SQL
against a real database; no shortcut around having the actual file present.
Status: done. data/olist.db and the updated .gitignore should be part of
the same commit as questions.yaml.

### 2026-08-22 — questions.yaml generated and live-validated (100/100)
Decision: all 100 ground-truth SQL queries executed against data/olist.db
during generation, re-verified after writing by parsing the YAML fresh and
re-running every query from the file itself. Tier distribution 10/25/25/25/15
matches spec. q066 was rephrased after execution revealed the original
premise was false — no state has a negative average delivery delay in this
data (range +8.7 to +20.7 days) — corrected to "states averaging under 11
days," a real 6-of-27 split.
Why: this is the concrete case the validation requirement existed for —
plausible-sounding ground truth that's actually wrong, caught before it
entered the eval set instead of silently deflating every architecture's
accuracy score equally (which would've been invisible in the final
comparison, since a systematically wrong question fails everyone the same
way and wouldn't show up as a suspicious outlier).
Status: done.

### 2026-08-22 — Exception: Claude Code writes questions.yaml, with validation
Decision: the 100 eval questions + ground-truth SQL (evals/questions.yaml)
are generated by Claude Code directly, not hand-typed — narrow exception to
the standing "everything hand-typed" rule. Condition: every ground-truth SQL
query must be executed against data/olist.db during generation and confirmed
to return a non-error, non-empty (unless genuinely expected empty) result
before being written to the file.
Why: this is data entry, not logic — the value of hand-typing was building
understanding of decisions (float tolerance, retry caps), which doesn't
apply to writing 100 individual questions. More importantly, chat cannot
validate SQL against the real warehouse at all; Claude Code can, so letting
it generate here is strictly safer than chat hand-writing unverified SQL.
scorer.py itself remains hand-typed — this exception covers questions.yaml
only.
Status: decided.

### 2026-08-22 — Eval stratification and scorer match semantics
Decision: 100 questions across 5 complexity tiers (single-table:10,
two-table:25, multi-table:25, aggregation+grouping:25, edge-case:15).
Scorer match semantics: column names/order ignored (compare row-wise sorted
value-tuples, same column count required); row order ignored unless a
question is explicitly marked ordered: true in questions.yaml; floats
compared via math.isclose(rel_tol=1e-4, abs_tol=1e-6); NULL matches NULL.
Why: sorting values within each row makes column aliasing/ordering
irrelevant without requiring name matches, which the agent can't be
expected to replicate exactly. Order-sensitivity as explicit per-question
metadata avoids the scorer guessing intent from phrasing. Relative float
tolerance handles both large currency sums and small ratio columns in the
same schema without one tolerance being wrong for the other.
Status: decided, ready for questions.yaml authoring and scorer.py build.

### 2026-08-22 — Eval schema scope: raw + staging, marts excluded
Decision: the agent's queryable schema is the raw and staging tables only —
customers, geolocation, order_items, order_payments, order_reviews, orders,
products, sellers, category_translation, stg_customers, stg_order_items,
stg_orders. Excluded: customer_features (mart) and int_customer_orders
(intermediate) — both are pre-aggregated to customer/order grain and would
make most eval questions trivial single-table lookups instead of real
multi-table SQL. Duplicate tables 'product' and 'order_payment' are dropped
entirely (kept 'products' and 'order_payments').
Why: the actual warehouse doesn't match PROJECT_BRIEF.md's assumed
dim_/fct_ marts layer — it's raw tables + a thin staging layer + one wide
mart. Raw/staging has the join richness a text-to-SQL eval needs; the mart
would flatten most questions into WHERE/ORDER BY with no joins.
Note: stg_orders is NOT a duplicate of orders — it's filtered to delivered
orders only (96,478 vs 99,441 rows) and adds a computed delivery_delay_days
column. Ground-truth SQL must deliberately choose orders vs stg_orders based
on whether the question is about all orders or specifically delivery timing
— this ambiguity is real and intentional, not a schema bug.
Status: decided, schema locked for eval question writing.

### 2026-08-05 — Claude Code used in plan mode only, all implementation hand-written
Decision: Claude Code is never used to write code directly into the codebase.
Used in plan mode as a thinking/design tool — propose an approach, review it,
then implementation is typed by hand. This applies to everything, not just
evals/scorer.py and src/graph/ as originally scoped in PROJECT_BRIEF.md §4.
Why: overrides the original "let Claude Code write scaffolding/cache/budget/llm"
split. Preference is to have written every line personally, including the
"nobody will ask about a hash function" pieces — more defensible in interviews,
and more actual practice.
Status: decided, applies from Phase 0 (budget.py/cache.py/llm.py) onward.


### 2026-08-05 — Work PC (RTX 3050, confirmed) is a real inference machine
Decision: drop the "Mac-only for live model calls" restriction. Confirmed via
nvidia-smi: llama-server.exe runs as a GPU compute process, Qwen2.5-Coder-7B
(Q4) uses ~5.16GB of the 3050's 6GB VRAM. Both machines can run Phase 1
verification, baseline runs, and agent runs.
Why: originally assumed only the M3 Pro Mac was capable. Work PC has a
dedicated GPU and handles the 7B model fine, but headroom is thin (~1GB
free) — watch for silent CPU fallback if context grows (long schema-retrieval
prompts, multi-turn self-correction) or if something else claims GPU memory
concurrently. If a run feels slow, check `ollama ps` before assuming it's a
model quality issue.
Status: confirmed working, 2026-08-05.


### 2026-08-05 — Work PC (RTX 3050) is a real inference machine, not just plumbing
Decision: drop the "Mac-only for live model calls" restriction. Ollama runs
with CUDA acceleration on Windows; Qwen2.5-Coder-7B at Q4 quantization
(~4.7GB) fits comfortably on the RTX 3050. Both machines can run Phase 1
verification, baseline runs, and agent runs — not just one.
Why: original assumption was M3 Pro Mac as the only capable hardware. Work
PC turns out to have a dedicated GPU (12700K / 32GB RAM / RTX 3050), which
handles a 7B model fine. No reason to gate real inference work behind being
at home.
Status: decided. Install Ollama for Windows on work PC, pull the same
qwen2.5-coder:7b tag, confirm GPU offload with `ollama ps` (should show
100% GPU, not CPU) before treating it as equivalent to the Mac.


<!-- Example entry format:

### 2026-08-05 — Float tolerance in scorer.py
Decision: compare numeric columns with `abs(a - b) < 1e-6` rather than exact
equality; anything looser risks masking real aggregation bugs.
Why: SQL engines can return floating point results that differ in the last
few decimal places for identical logical queries (summation order, casting).
Exact match would fail correct SQL; anything looser than 1e-6 starts hiding
genuine errors like wrong GROUP BY granularity.
Status: decided, not yet implemented.

### 2026-08-05 — uv for environment management, dual-machine workflow
Decision: pyproject.toml + committed uv.lock instead of requirements.txt.
git is the sync mechanism between Windows work PC and macOS home machine;
DECISIONS.md + README.md are the design-state continuity mechanism.
Why: uv.lock guarantees identical dependency resolution on both OSes without
manual version pinning. Ollama/Qwen only run on the Mac, so Windows sessions
are scoped to plumbing/logic/design work that doesn't need live model calls.
Status: decided, scaffolded.

-->
