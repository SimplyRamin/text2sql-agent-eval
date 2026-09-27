# =================================================================================================
#                                           Written by Ramin F.
#                                           Senior AI Engineer
#                            Ferdos.ramin@gmail.com | simplyramin.github.io
# =================================================================================================

import argparse
import csv
import os
import re
import time
from datetime import datetime
from pathlib import Path

import duckdb

from evals.scorer import DB_PATH, load_questions, score_question
from src import llm

TABLES = [
    "orders", "stg_orders", "customers", "stg_customers",
    "order_items", "stg_order_items", "order_payments",
    "order_reviews", "products", "sellers",
    "category_translation", "geolocation",
]

FENCE_PATTERN = re.compile(r"```(?:sql)?\s*\n?(.*?)```", re.DOTALL | re.IGNORECASE)
SQL_START_PATTERN = re.compile(r"(SELECT|WITH)\b", re.IGNORECASE)

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"


def build_schema_string(tables: list[str] = TABLES) -> str:
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        blocks = []
        for table in tables:
            columns = con.sql(f"DESCRIBE {table}").fetchall()
            column_lines = ",\n ".join(f"{name} {dtype}" for name, dtype, *_ in columns)
            blocks.append(f"CREATE TABLE {table} (\n  {column_lines}\n);")
        return "\n\n".join(blocks)
    finally:
        con.close()


def build_prompt(schema: str, question: str) -> str:
    return f"""You are a SQL expert working with a DuckDB database.

Given the following schema:

{schema}

Write a SQL query to answer this question:
{question}

Return only the SQL query. Do not include any explanation.
"""


def extract_sql(response_text: str) -> str:
    fences = FENCE_PATTERN.findall(response_text)
    for fence_content in fences:
        if SQL_START_PATTERN.search(fence_content):
            sql = fence_content.strip()
            break
    else:
        match = SQL_START_PATTERN.search(response_text)
        sql = response_text[match.start():].strip() if match else response_text.strip()

    semicolon_index = sql.find(";")
    if semicolon_index != -1:
        sql = sql[: semicolon_index + 1]

    return sql


def run_baseline(questions: list[dict], model: str, provider: str) -> list[dict]:
    schema = build_schema_string()
    results = []

    for question in questions:
        prompt = build_prompt(schema, question["question"])
        start_time = time.perf_counter()

        try:
            response = llm.complete(prompt, model=model, provider=provider, temperature=0.0)
        except Exception as e:
            sql = ""
            correct = False
            error = str(e)
            cost = 0.0
            in_tokens = 0
            out_tokens = 0
            llm_latency_ms = 0.0
        else:
            sql = extract_sql(response["text"])
            scored = score_question(question, sql)
            correct = scored["correct"]
            error = scored["error"]
            cost = response["cost"]
            in_tokens = response["usage"]["in_tokens"]
            out_tokens = response["usage"]["out_tokens"]
            llm_latency_ms = response["latency_ms"]

        wall_clock_ms = (time.perf_counter() - start_time) * 1000
        
        status = "PASS" if correct else "FAIL"
        line = f"{question['id']} tier={question['tier']} {status}"
        if not correct and error:
            line += f" - {error}"
        print(line)

        results.append({
            "id": question["id"],
            "tier": question["tier"],
            "category": question["category"],
            "correct": correct,
            "error": error,
            "generated_sql": sql,
            "cost": cost,
            "in_tokens": in_tokens,
            "out_tokens": out_tokens,
            "llm_latency_ms": llm_latency_ms,
            "wall_clock_ms": wall_clock_ms,
        })

    return results


def write_csv(results: list[dict], model: str) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    model_slug = model.replace(":", "-").replace("/", "-")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = RESULTS_DIR / f"baseline_{model_slug}_{timestamp}.csv"

    fieldnames = [
        "id", "tier", "category", "correct", "error", "generated_sql",
        "cost", "in_tokens", "out_tokens", "llm_latency_ms", "wall_clock_ms",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    return path


def print_summary(results: list[dict]) -> None:
    total = len(results)
    correct_total = sum(1 for r in results if r["correct"])
    pct = (correct_total / total * 100) if total else 0.0

    print(f"\nOverall accuracy: {correct_total}/{total} ({pct:.1f}%)")
    print("\nBy tier:")

    for tier in sorted(set(r["tier"] for r in results)):
        tier_results = [r for r in results if r["tier"] == tier]
        tier_correct = sum(1 for r in tier_results if r["correct"])
        tier_total = len(tier_results)
        tier_pct = (tier_correct / tier_total * 100) if tier_total else 0.0
        print(f"    Tier {tier}: {tier_correct}/{tier_total} ({tier_pct:.1f}%)")


def main():
    parser = argparse.ArgumentParser(description="Phase 4 dumb baseline: single-call SQL generation.")
    parser.add_argument("--limit", type=int, default=None, help="Run only the first N questions (dry-run).")
    parser.add_argument("--model", type=str, default=None, help="Model tag to use.")
    parser.add_argument("--provider", type=str, default="local", choices=["local", "hosted"], help="Which provider to use.")
    parser.add_argument("--dry-run", action="store_true", help="Estimate cost without making any LLM calls.")
    args = parser.parse_args()

    if args.provider == "local":
        model = args.model or os.getenv("OLLAMA_MODEL")
        if not model:
            raise RuntimeError("No model specified and OLLAMA_MODEL is not set in .env")
    else:
        if not args.model:
            from src.llm import PRICING
            raise RuntimeError(
                f"--provider hosted requires --model to be specified explicitly. "
                f"Valid models with pricing configured: {list(PRICING.keys())}"
            )
        model = args.model

    questions = load_questions()
    if args.limit is not None:
        questions = questions[: args.limit]

    if args.dry_run:
        from src.dry_run import dry_run_baseline
        schema = build_schema_string()
        estimate = dry_run_baseline(questions, model, schema)
        print(f"Dry run: {len(questions)} questions, model={model}, provider={args.provider}\n")
        print(f"{estimate['num_calls']} calls, "
              f"{estimate['total_in_tokens']:.0f} in / {estimate['total_out_tokens']:.0f} out tokens, "
              f"${estimate['total_cost']:.4f}")
        return

    print(f"Running baseline: model={model}, provider={args.provider}, questions={len(questions)}\n")

    results = run_baseline(questions, model=model, provider=args.provider)
    path = write_csv(results, model=model)
    print_summary(results)

    print(f"\nResults written to: {path}")


if __name__ == "__main__":
    main()