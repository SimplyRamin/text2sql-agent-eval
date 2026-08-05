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
