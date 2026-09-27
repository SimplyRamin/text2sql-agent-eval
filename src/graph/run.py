# =================================================================================================
#                                           Written by Ramin F.
#                                           Senior AI Engineer
#                            Ferdos.ramin@gmail.com | simplyramin.github.io
# =================================================================================================

import argparse
import csv
import os
import statistics
import time
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
        "retries_used", "initial_retrieved_tables", "route",
        "cost", "in_tokens", "out_tokens", "llm_latency_ms", "wall_clock_ms",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    return path


def print_route_summary(results: list[dict]) -> None:
    routes = sorted(set(r["route"] for r in results if r["route"]))
    if not routes:
        return

    print("\nBy route:")
    for route in routes:
        route_results = [r for r in results if r["route"] == route]
        correct = sum(1 for r in route_results if r["correct"])
        total = len(route_results)
        pct = (correct / total * 100) if total else 0.0
        print(f" {route}: {correct}/{total} ({pct:.1f}%)")

    wall_clocks = [r["wall_clock_ms"] for r in results]
    total_tokens = sum(r["in_tokens"] + r["out_tokens"] for r in results)
    print(f"\nWall-clock: mean={statistics.mean(wall_clocks):.0f}ms, median={statistics.median(wall_clocks):.0f}ms")
    print(f"Total tokens: {total_tokens}")

def build_initial_state(question: dict, model: str, provider: str) -> GraphState:
    return GraphState(
        question=question,
        model=model,
        provider=provider,
        schema_context="",
        retrieved_tables=[],
        initial_retrieved_tables=[],
        sql="",
        correct=False,
        error=None,
        retry_count=0,
        route="",
        total_cost=0.0,
        total_in_tokens=0,
        total_out_tokens=0,
        total_llm_latency_ms=0.0,
    )


def run_agent(questions: list[dict], model: str, provider: str) -> list[dict]:
    graph = build_graph()
    results = []

    for question in questions:
        initial_state = build_initial_state(question, model, provider)
        start_time = time.perf_counter()
        final_state = graph.invoke(initial_state)
        wall_clock_ms = (time.perf_counter() - start_time) * 1000

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
            "route": final_state["route"],
            "cost": final_state["total_cost"],
            "in_tokens": final_state["total_in_tokens"],
            "out_tokens": final_state["total_out_tokens"],
            "llm_latency_ms": final_state["total_llm_latency_ms"],
            "wall_clock_ms": wall_clock_ms,
        })
    return results


def main():
    parser = argparse.ArgumentParser(description="Phase 5/6 LangGraph agent: schema retrieval + capped self-correction + routing.")
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
        from src.dry_run import dry_run_routed
        estimate = dry_run_routed(questions, model)
        print(f"Dry run: {len(questions)} questions, model={model}, provider={args.provider}\n")
        for label in ["floor", "empirical", "ceiling"]:
            e = estimate[label]
            print(f"{label.capitalize()}: {e['num_calls']} calls, "
                  f"{e['total_in_tokens']:.0f} in / {e['total_out_tokens']:.0f} out tokens, "
                  f"${e['total_cost']:.4f}")
        return

    print(f"Running agent: model={model}, provider={args.provider}, questions={len(questions)}\n")

    results = run_agent(questions, model=model, provider=args.provider)
    path = write_csv(results, model=model)
    print_summary(results)
    print_route_summary(results)

    print(f"\nResults written to: {path}")


if __name__ == "__main__":
    main()