# text2sql-agent-eval

**Live results explorer:** https://YOUR-USERNAME.github.io/text2sql-agent-eval/

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
mechanism is: **git is the sync layer, `uv.lock` is the environment
guarantee, `README.md` + `DECISIONS.md` are the design-state guarantee.**

**Every session, either machine:**
1. `git pull` before doing anything
2. `uv sync` if `pyproject.toml` or `uv.lock` changed since last pull
3. Read `DECISIONS.md` for anything decided in chat since last session
4. Work
5. `git add -A && git commit -m "..." && git push` before closing the laptop —
   don't leave uncommitted work sitting on one machine only

**Both machines run real local inference.** Work PC (i7-12700K, 32GB RAM,
RTX 3050) runs Ollama with CUDA acceleration; Qwen2.5-Coder-7B at Q4
quantization is ~4.7GB and fits the GPU with headroom. Mac (M3 Pro) runs it
via Metal. Confirm GPU offload on either machine with `ollama ps` before
trusting a run — if it falls back to CPU, generation will be visibly slower
and that's worth catching before you attribute a timing result to the model
rather than the hardware.

**Cache doesn't sync — that's intentional but has one sharp edge.**
`cache/` is gitignored. For local Ollama calls that's fine, they're free to
regenerate on either machine. For Phase 7's hosted comparison runs, a
non-synced cache means switching machines mid-run risks re-paying for calls
already made on the other machine. Do Phase 7 (hosted runs) in one sitting,
on one machine.

**`.env` is per-machine, never committed.** Both machines set `OLLAMA_HOST`
and `OLLAMA_MODEL` now — no machine-specific fallback needed for local
inference anymore. `API_BASE_URL` / `API_KEY` for the hosted reseller only
get filled in when you're actually doing a Phase 7 run.

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

Complete. All phases (0-9) finished. Final comparison:

| | Baseline | Routed agent |
|---|---|---|
| Local (Qwen2.5-Coder-7B) | 66% | 69% |
| Hosted (gpt-4o-mini) | 79% | **84%** |

See `README_RESULTS.md` for the full comparison table and narrative, and
`FAILURE_TAXONOMY.md` for the six-category failure-mode breakdown behind
these numbers — including two real bugs found and fixed during
evaluation (a scorer tolerance issue and a dedup-checklist gap), both
documented with the evidence that caught them.

`DECISIONS.md` has the complete build log: every architectural choice,
bug found, and fix applied across all nine phases, from the original
eval-harness design through the final hosted comparison run.