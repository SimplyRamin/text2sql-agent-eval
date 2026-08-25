# =================================================================================================
#                                           Written by Ramin F.
#                                           Senior AI Engineer
#                            Ferdos.ramin@gmail.com | simplyramin.github.io
# =================================================================================================

import argparse
import csv
import os
import re
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


def run_baseline(questions: list[dict], model: str) -> list[dict]:
    schema = build_schema_string()
    results = []

    for question in questions:
        prompt = build_prompt(schema, question["question"])

        try:
            response = llm.complete(prompt, model=model, provider="local", temperature=0.0)
        except Exception as e:
            sql = ""
            correct = False
            error = str(e)
        else:
            sql = extract_sql(response["text"])
            scored = score_question(question, sql)
            correct = scored["correct"]
            error = scored["error"]

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
        })

    return results


def write_csv(results: list[dict], model: str) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    model_slug = model.replace(":", "-").replace("/", "-")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = RESULTS_DIR / f"baseline_{model_slug}_{timestamp}.csv"

    fieldnames = ["id", "tier", "category", "correct", "error", "generated_sql"]
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
    parser.add_argument("--model", type=str, default=os.getenv("OLLAMA_MODEL"), help="Ollama model tag to use.")
    args = parser.parse_args()

    if not args.model:
        raise RuntimeError("No model specified and OLLAMA_MODEL is not set in .env")

    questions = load_questions()
    if args.limit is not None:
        questions = questions[: args.limit]

    print(f"Running baseline: model={args.model}, questions={len(questions)}\n")

    results = run_baseline(questions, model=args.model)
    path = write_csv(results, model=args.model)
    print_summary(results)

    print(f"\nResults written to: {path}")


if __name__ == "__main__":
    main()