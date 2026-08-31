# =================================================================================================
#                                           Written by Ramin F.
#                                           Senior AI Engineer
#                            Ferdos.ramin@gmail.com | simplyramin.github.io
# =================================================================================================

import argparse
import csv
import os
from datetime import datetime
from pathlib import Path

from evals.scorer import load_questions
from src.baseline import print_summary
from src.graph.graph import build_graph
from src.graph.state import GraphState

RESULTS_DIR = Path(__file__).resolve().parent.parent.parent / "results"


def write_csv(results: list[dict], model: str) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    model_slug = model.replace(":", "-").replace("/", "-")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = RESULTS_DIR / f"agent_{model_slug}_{timestamp}.csv"

    fieldnames = [
        "id", "tier", "category", "correct", "error", "generated_sql",
        "retries_used", "initial_retrieved_tables",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    return path


def build_initial_state(question: dict, model: str) -> GraphState:
    return GraphState(
        question=question,
        model=model,
        schema_context="",
        retrieved_tables=[],
        initial_retrieved_tables=[],
        sql="",
        correct=False,
        error=None,
        retry_count=0,
    )


def run_agent(questions: list[dict], model: str) -> list[dict]:
    graph = build_graph()
    results = []

    for question in questions:
        initial_state = build_initial_state(question, model)
        final_state = graph.invoke(initial_state)

        retries_used = final_state["retry_count"] - 1
        status = "PASS" if final_state["correct"] else "FAIL"
        line = f"{question['id']} tier={question['tier']} {status} retries={retries_used}"
        if not final_state["correct"] and final_state["error"]:
            line += f" - {final_state['error']}"
        print(line)

        results.append({
            "id": question["id"],
            "tier": question["tier"],
            "category": question["category"],
            "correct": final_state["correct"],
            "error": final_state["error"],
            "generated_sql": final_state["sql"],
            "retries_used": retries_used,
            "initial_retrieved_tables": ",".join(final_state["initial_retrieved_tables"]),
        })

    return results


def main():
    parser = argparse.ArgumentParser(description="Phase 5 LangGraph agent: schema retrieval + capped self-correction.")
    parser.add_argument("--limit", type=int, default=None, help="Run only the first N questions (dry-run).")
    parser.add_argument("--model", type=str, default=os.getenv("OLLAMA_MODEL"), help="Ollama model tag to use.")
    args = parser.parse_args()

    if not args.model:
        raise RuntimeError("No model specified and OLLAMA_MODEL is not set in .env")

    questions = load_questions()
    if args.limit is not None:
        questions = questions[: args.limit]

    print(f"Running agent: model={args.model}, questions={len(questions)}\n")

    results = run_agent(questions, model=args.model)
    path = write_csv(results, model=args.model)
    print_summary(results)

    print(f"\nResults written to: {path}")


if __name__ == "__main__":
    main()