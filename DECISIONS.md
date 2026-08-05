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
