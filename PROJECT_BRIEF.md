# text2sql-agent-eval — Project Brief

Carry this file into the new project. Commit it to the repo root so Claude Code reads it
at the start of every session.

---

## 1. Context primer

Paste this block into the **first chat message** of the new project.

```
CONTEXT — carry-over from a previous project.

WHO: Ramin Ferdos, Senior AI Engineer, 7+ years, based in Tehran, currently at
Tabiat Makan Industrial Group (FMCG holding). Job searching internationally for
roles requiring visa sponsorship — UK, Netherlands, Germany, Finland, Norway,
Spain primary.

POSITIONING DECISION (already made, do not relitigate): applying as Senior AI
Engineer, not Data Scientist. The last 14 months of work is agent orchestration,
RAG, and production ML systems; sponsorship is easier to justify for a thinner
applicant pool; DS evidence at senior level is weaker. Causal inference and
experimentation are the 3-5 year direction, deliberately parked.

WHY THIS PROJECT: All of my strongest work — a 14-agent LLM analytics platform,
a RAG chatbot across 5 knowledge bases, a production PWA — lives in private org
repos no recruiter can see. My only public artifacts are a churn model and a
full-stack app, which read as data science and web dev, not AI engineering. This
project is the public mirror of the private work.

WHAT: A text-to-SQL analytics agent over an Olist e-commerce warehouse I already
built (dbt staging -> intermediate -> marts, 6 data quality tests, Prefect
orchestration). LangGraph for the agent. The POINT of the project is the
evaluation harness, not the agent — execution accuracy against ground truth,
compared across architectures.

BUILD ORDER (non-negotiable — evals come FIRST):
1. Eval harness + ~100 stratified questions with ground-truth SQL. No LLM needed.
2. Dumb baseline: one call, schema in prompt, SQL out. Record accuracy.
3. LangGraph agent: schema retrieval, generation, execution, capped self-correction.
4. Routing + specialist paths. Measure accuracy AND cost AND latency.
5. Write-up: comparison table + failure taxonomy.

HARD CONSTRAINTS:
- Total budget: $3 ceiling enforced in code (budget.py raises, not warns).
- Develop entirely against LOCAL Qwen2.5-Coder-7B via Ollama on an M3 Pro Mac.
  Hosted API calls ONLY for final comparison runs.
- Content-hashed disk cache on every call. temperature=0 throughout.
- Cap self-correction retries at 2.
- Schema retrieval, not full-schema-in-prompt.
- Provider-agnostic LLM wrapper (LiteLLM or ~10 lines) — using an Iranian-accessible
  API reseller, so endpoints may be unstable.
- Dry-run token estimate before EVERY paid run. Then 10 questions, check, then 90.

TOOLING: Claude Code builds. Chat decides. See PROJECT_BRIEF.md in the repo.

KNOWN GAPS this project closes: LangGraph/LangChain (no production experience),
and having any publicly inspectable agentic system at all.
```

---

## 2. Repo setup — do this before any chat

**Name:** `text2sql-agent-eval` — public from day one.

"Text-to-SQL" is a term a recruiter parses instantly. "eval" in the name signals the
differentiator before anyone clicks.

```
text2sql-agent-eval/
├── README.md
├── PROJECT_BRIEF.md       # this file
├── DECISIONS.md           # the chat <-> Claude Code bridge (see §3)
├── .gitignore
├── .env.example
├── pyproject.toml         # uv-managed deps
├── uv.lock
├── data/                  # Olist warehouse (DuckDB or Postgres init)
├── evals/
│   ├── questions.yaml     # ~100 questions + ground-truth SQL
│   └── scorer.py          # execution-accuracy comparison  [WRITE YOURSELF]
├── src/
│   ├── budget.py          # hard spend ceiling
│   ├── cache.py           # content-hashed disk cache
│   ├── llm.py             # provider-agnostic wrapper
│   ├── baseline.py        # Stage 2: single-call
│   └── graph/             # Stage 3+: LangGraph nodes  [WRITE YOURSELF]
├── results/               # per-run CSVs — commit these
└── README_RESULTS.md      # the comparison table
```

**Before the first commit,** `.gitignore` must contain:

```
.env
cache/
__pycache__/
*.duckdb
.venv/
```

API keys live in `.env` only. Never in code, never in a notebook cell. A leaked reseller
key is a real financial loss, not a theoretical one.

Commit `results/` CSVs deliberately. Reproducible numbers in version control is part of
what makes this credible.

---

## 3. How chat and Claude Code fit together

**They share nothing.** Separate contexts, no shared memory. Claude Code can debug for two
hours and chat will know none of it. Chat can design your whole eval methodology and Claude
Code will never have seen it.

**The bridge is `DECISIONS.md`.** Every time chat helps you decide something — how result
matching handles floats, why retries cap at two, what the difficulty tiers mean — write it
there and commit. Claude Code reads the repo, so it picks the decision up automatically.

End a chat design session by asking for the decision as a markdown block. Paste, commit,
move on. Going the other direction — Code to chat — paste the file or the results CSV.
Chat cannot read your disk.

### Which one to use

The line is **decisions versus construction**, not hard versus easy.

| Use chat when | Use Claude Code when |
|---|---|
| Nothing exists on disk yet | A file needs to change or run |
| The answer is a judgment call | The answer is an implementation |
| You'd want to argue about it | You'd want it tested |

**The test that resolves most cases: can you point at a file?** If yes, Claude Code. If
you're still deciding what the file should contain, chat.

### Failure modes to watch

- **Drifting into chat mid-build.** When Code is stuck, the cause is usually a missing
  *decision*, not a missing capability. Go to chat for the decision only, write it down,
  come back. Don't start pasting code fragments.
- **Letting Code make design calls.** It will pick something reasonable and you'll never
  examine it. Those are exactly the choices that determine whether your numbers mean
  anything.

**Start every Claude Code session** by having it read `README.md` and `DECISIONS.md`.
Sessions don't persist; those two files are your continuity.

---

## 4. What you write yourself

**Write yourself — the two files you'll be asked about in interviews:**

- `evals/scorer.py` — the intellectual core. ~150 lines. Float tolerance, column ordering,
  NULL handling, ties. When someone asks "how did you handle result sets coming back in a
  different column order," you want to remember *making* that call.
- `src/graph/` — the LangGraph nodes. State passing, conditional edges, the retry loop.
  This is the LangGraph experience you're building the project to acquire.

Generated code you reviewed and code you wrote read identically and defend completely
differently. Roughly 8 hours of work.

**Let Claude Code write:** scaffolding, `cache.py`, `budget.py`, `llm.py`, the 100
questions, glue, plumbing. Nobody will ask about a hash function and an exception class.

**Middle mode that works well:** Code writes the tests, you write the implementation. Have
it enumerate scorer test cases — float tolerance, ordering, NULLs, empty results — and you
make them pass. You get the design thinking; it does the enumeration you'd get bored of.

**Plan mode:** use it at the start of each phase as a thinking tool. Ask for the plan, read
it, argue with it, then decide whether you're implementing or delegating. Turn it off when
you're fixing the same traceback for the fourth time.

**Standing instruction for Claude Code, day one:** *never make a hosted API call without
asking me first.* Local Ollama unlimited; anything billable, ask. That single rule protects
the budget better than any tracker.

---

## 5. Phase sequence

| # | Phase | Where | Model | Cost |
|---|---|---|---|---|
| 0 | Repo scaffold, `budget.py`, `cache.py`, `llm.py` | Claude Code | Sonnet | $0 |
| 1 | Ollama + Qwen2.5-Coder-7B, verify SQL generation | Claude Code | Sonnet | $0 |
| 2 | **Eval set design** — stratification, match semantics | Chat | **Opus** | $0 |
| 3 | Write 100 questions + scorer | Code writes questions / **you write scorer** | Sonnet | $0 |
| 4 | Baseline (Stage 2), local model | Claude Code | Sonnet | $0 |
| 5 | LangGraph agent (Stage 3) | **You write nodes** | Sonnet | $0 |
| 6 | Routing + specialists (Stage 4) | **You write nodes** | Sonnet | $0 |
| 7 | Hosted comparison runs | Claude Code | Sonnet | ~$0.50 |
| 8 | **Interpret results, failure taxonomy** | Chat | **Opus** | $0 |
| 9 | Write-up + README | Chat | **Opus** | $0 |

**Do Phase 0 and 1 in one session.** Working local inference plus a budget class that
raises on limit means everything after is safe to iterate on freely.

**Phase 2 is the one that deserves real thought.** Get the questions and matching logic
wrong and every number downstream is noise.

**The temptation will be to skip Phases 2-3 and jump to the agent**, because the agent is
the fun part. Don't. The eval set is what makes this a senior artifact rather than another
LangGraph demo, and building it first is what forces the agent to be honest.

---

## 6. Budget discipline

Ceiling set at **$3**, not $5 — leave headroom for the mistake you haven't thought of.

```python
class Budget:
    def __init__(self, limit_usd=3.00):
        self.limit, self.spent = limit_usd, 0.0
    def charge(self, in_tok, out_tok, price_in, price_out):
        cost = (in_tok/1e6)*price_in + (out_tok/1e6)*price_out
        if self.spent + cost > self.limit:
            raise RuntimeError(f"Budget exhausted: ${self.spent:.4f}")
        self.spent += cost
        return cost
```

Cache key: `sha256(f"{model}|{temperature}|{prompt}")`. Store responses as JSON files.
This is the single biggest saver — you'll burn money re-running evals after changing
something unrelated to the model.

Add a `--dry-run` flag that walks the eval, counts tokens with `tiktoken`, prints projected
cost, and exits. Never launch a paid run without it. Then run 10 questions, check output
and cost, then run the remaining 90.

**Where money leaks, ranked:**

1. Uncapped self-correction loops — cap at 2, log every retry
2. Full schema in every prompt — ~4,000 tokens vs ~800 retrieved
3. Forgetting to switch models back after a test

**Spending plan:** Phases 0-6 local, $0. Comparison runs ~$0.50. Contingency $2.50.
You'll likely finish under a dollar.

---

## 7. What this produces

A resume bullet with real numbers instead of adjectives, and — more importantly — forty
minutes of specific things to say about *why* particular queries failed. That specificity
is exactly what was missing in the Holidu conversation.

The comparison table is the artifact. Local 7B at X% execution accuracy, hosted model at
Y%, at Z times the cost per query, with a breakdown of where the gap actually sits. Almost
nobody in the applicant pool has that.

Deploy the demo on Hugging Face Spaces alongside Mosaic. Pin it on GitHub.
