# =================================================================================================
#                                           Written by Ramin F.
#                                   for Tabiat Makan Industrial Group
# =================================================================================================

import csv
import os
from pathlib import Path

import tiktoken

from src.llm import PRICING

_REPO_ROOT = Path(__file__).resolve().parent.parent
BASELINE_REFERENCE_CSV = _REPO_ROOT / "results" / "baseline_qwen2.5-coder-7b_20260825_154930.csv"
ROUTED_REFERENCE_CSV = _REPO_ROOT / "results" / "agent_qwen2.5-coder-7b_20260902_120509.csv"

_TIKTOKEN_CACHE_DIR = _REPO_ROOT / ".tiktoken_cache"
_TIKTOKEN_CACHE_DIR.mkdir(exist_ok=True)
os.environ.setdefault("TIKTOKEN_CACHE_DIR", str(_TIKTOKEN_CACHE_DIR))


def count_tokens(text: str, model: str) -> int:
    try:
        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except Exception:
        # Network unavailable and no local cache — fall back to a crude
        # but clearly conservative estimate. ~4 characters per token is
        # the standard rule of thumb for English/code text; biased toward
        # overestimating, matching this module's whole purpose (better to
        # overshoot a cost projection than undershoot one).
        return max(1, len(text) // 4)

def estimate_avg_output_tokens(csv_path: str, model: str) -> float:
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError(f"No rows found in {csv_path}")
    token_counts = [count_tokens(row["generated_sql"], model) for row in rows]
    return sum(token_counts) / len(token_counts)


def estimate_retry_rate(csv_path: str) -> float:
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError(f"No rows found in {csv_path}")
    retry_counts = [int(row["retries_used"]) for row in rows]
    return sum(retry_counts) / len(retry_counts)


def project_cost(input_texts: list[str], model: str, avg_output_tokens: float) -> dict:
    if model not in PRICING:
        raise RuntimeError(f"No pricing entry for model '{model}' - add it to PRICING")

    price_in, price_out = PRICING[model]

    total_in_tokens = sum(count_tokens(t, model) for t in input_texts)
    total_out_tokens = avg_output_tokens * len(input_texts)

    cost_in = (total_in_tokens / 1e6) * price_in
    cost_out = (total_out_tokens / 1e6) * price_out

    return {
        "num_calls": len(input_texts),
        "total_in_tokens": total_in_tokens,
        "total_out_tokens": total_out_tokens,
        "cost_in": cost_in,
        "cost_out": cost_out,
        "total_cost": cost_in + cost_out,
    }


def dry_run_baseline(questions: list[dict], model: str, schema: str) -> dict:
    from src.baseline import build_prompt

    prompts = [build_prompt(schema, q["question"]) for q in questions]
    avg_output_tokens = estimate_avg_output_tokens(BASELINE_REFERENCE_CSV, model)

    return project_cost(prompts, model, avg_output_tokens)


def dry_run_routed(questions: list[dict], model: str) -> dict:
    from src.baseline import TABLES, build_prompt, build_schema_string
    from src.graph import prompts as join_prompts
    from src.graph.retrieval import count_entity_groups, retrieve_tables

    attempt_1_prompts = []
    for q in questions:
        retrieved = retrieve_tables(q["question"])
        schema = build_schema_string(retrieved)
        groups = count_entity_groups(retrieved)

        if groups >= 3:
            prompt = join_prompts.build_join_prompt(schema, q["question"], retrieved)
        else:
            prompt = build_prompt(schema, q["question"])

        if "category_translation" in retrieved:
            prompt += f"\n{join_prompts.CATEGORY_NAME_NOTE}\n"

        attempt_1_prompts.append(prompt)

    avg_output_tokens = estimate_avg_output_tokens(ROUTED_REFERENCE_CSV, model)
    retry_rate = estimate_retry_rate(ROUTED_REFERENCE_CSV)

    floor = project_cost(attempt_1_prompts, model, avg_output_tokens)

    empirical_retry_prompts = attempt_1_prompts * round(retry_rate)
    empirical = project_cost(attempt_1_prompts + empirical_retry_prompts, model, avg_output_tokens)

    full_schema = build_schema_string(TABLES)
    placeholder_sql = "SELECT 1;"
    placeholder_error = "placeholder error text for estimation purposes"
    ceiling_retry_prompts = []
    for q in questions:
        retry_prompt = join_prompts.build_join_retry_prompt(
            full_schema, q["question"], placeholder_sql, placeholder_error, TABLES
        )
        ceiling_retry_prompts.extend([retry_prompt, retry_prompt])

    ceiling = project_cost(attempt_1_prompts + ceiling_retry_prompts, model, avg_output_tokens)

    return {"floor": floor, "empirical": empirical, "ceiling": ceiling}