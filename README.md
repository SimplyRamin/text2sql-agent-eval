# text2sql-agent-eval

A text-to-SQL analytics agent over an Olist e-commerce warehouse (dbt staging ->
intermediate -> marts), evaluated for execution accuracy across architectures:
a single-call baseline, a LangGraph agent with schema retrieval and capped
self-correction, and a routed/specialist variant.

**The point of this project is the evaluation harness, not the agent.**
See `README_RESULTS.md` (once populated) for the comparison table and failure
taxonomy.

## Start here

- `PROJECT_BRIEF.md` — full context, build order, constraints. Read this first,
  every session.
- `DECISIONS.md` — the running log of design decisions made in chat. Read this
  second, every session.

## Environment (uv)

```bash
uv sync              # creates .venv, installs exact locked versions
uv run pytest        # run tests
uv run python -m src.baseline   # example — run a module
```

`uv.lock` is committed. `uv sync` on either machine reproduces the identical
dependency set — that's the whole point of committing it, see "Working across
two machines" below. Never `pip install` directly into the venv; always go
through `uv add <package>` so the lockfile stays authoritative.

## Working across two machines (Windows work PC / macOS home)

This project develops across two machines with no shared filesystem. The
mechanism is: **git is the sync layer, `uv.lock` is the environment guarantee,
`README.md` + `DECISIONS.md` are the design-state guarantee.**

**Every session, either machine:**
1. `git pull` before doing anything
2. `uv sync` if `pyproject.toml` or `uv.lock` changed since last pull
3. Read `DECISIONS.md` for anything decided in chat since last session
4. Work
5. `git add -A && git commit -m "..." && git push` before closing the laptop —
   don't leave uncommitted work sitting on one machine only

**What's Mac-only:** anything requiring a live call to local Ollama —
Phase 1 verification, actual baseline/agent runs, anything where you need to
see real model output rather than just correct plumbing. Ollama + Qwen2.5-Coder-7B
only run on the M3 Pro.

**What's fine on Windows:** scaffolding, `evals/questions.yaml` authoring,
`evals/scorer.py` logic (test it against fixture result sets, no LLM needed),
`src/budget.py` and `src/cache.py` logic and unit tests, LangGraph node
*structure* (state schema, conditional edges) using a stub/fake LLM function
in tests rather than a real one, and all chat/design work. Basically: anything
that doesn't need to observe real model behavior.

**Cache doesn't sync — that's intentional but has one sharp edge.**
`cache/` is gitignored. For local Ollama calls that's fine, they're free to
regenerate. For Phase 7's hosted comparison runs, a non-synced cache means
switching machines mid-run risks re-paying for calls already made on the other
machine. Do Phase 7 (hosted runs) in one sitting, on one machine.

**`.env` is per-machine, never committed.** Windows PC's `.env` can simply
omit `OLLAMA_HOST` — `src/llm.py` should treat that as "local model not
available here" rather than erroring the whole program.

## Build order

1. Eval harness + ~100 stratified questions with ground-truth SQL (no LLM needed)
2. Dumb baseline — single call, full schema in prompt
3. LangGraph agent — schema retrieval, generation, execution, capped self-correction
4. Routing + specialist paths
5. Write-up — comparison table + failure taxonomy

## Constraints

- $3 hard budget ceiling, enforced in `src/budget.py` (raises, not warns)
- Local Qwen2.5-Coder-7B via Ollama (Mac only) for all development; hosted API
  calls reserved for final comparison runs
- Content-hashed disk cache on every call, `temperature=0` throughout
- Self-correction capped at 2 retries
- Schema retrieval, not full-schema-in-prompt
- Dry-run token estimate before every paid run, then 10 questions, then 90

## Status

Repo scaffolded. Phase 0 in progress — see `DECISIONS.md` for what's been
decided so far.
