# =================================================================================================
#                                           Written by Ramin F.
#                                           Senior AI Engineer
#                            Ferdos.ramin@gmail.com | simplyramin.github.io
# =================================================================================================

from pathlib import Path

import gradio as gr
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]

ARCHS = {
    "local_baseline": {
        "label": "Local · baseline",
        "csv": ROOT / "results" / "baseline_qwen2.5-coder-7b_20260929_105034.csv",
    },
    "local_routed": {
        "label": "Local · routed agent",
        "csv": ROOT / "results" / "agent_qwen2.5-coder-7b_20260929_111951.csv",
    },
    "hosted_baseline": {
        "label": "Hosted · baseline",
        "csv": ROOT / "results" / "baseline_gpt-4o-mini_20260929_103950.csv",
    },
    "hosted_routed": {
        "label": "Hosted · routed agent",
        "csv": ROOT / "results" / "agent_gpt-4o-mini_20260929_105023.csv",
    },
}

QUESTIONS_PATH = ROOT / "evals" / "questions.yaml"


def _load_questions() -> dict:
    with open(QUESTIONS_PATH) as f:
        raw = yaml.safe_load(f)
    return {q["id"]: q for q in raw}


def _load_all_results() -> pd.DataFrame:
    frames = []
    for arch_key, info in ARCHS.items():
        df = pd.read_csv(info["csv"])
        df["arch"] = arch_key
        df["correct"] = df["correct"].astype(str).map({"True": True, "False": False})
        frames.append(df)
    return pd.concat(frames, ignore_index=True, sort=False)


QUESTIONS = _load_questions()
RESULTS = _load_all_results()


def _run_startup_checks():
    expected_ids = set(QUESTIONS.keys())
    assert len(expected_ids) == 100, f"Expected 100 questions, found {len(expected_ids)}"

    for arch_key in ARCHS:
        subset = RESULTS[RESULTS["arch"] == arch_key]
        assert len(subset) == 100, f"{arch_key}: expected 100 rows, found {len(subset)}"

        actual_ids = set(subset["id"])
        assert actual_ids == expected_ids, f"{arch_key}: id mismatch with questions.yaml"

        for _, row in subset.iterrows():
            q = QUESTIONS[row["id"]]
            assert str(row["tier"]) == str(q["tier"]), f"{arch_key}/{row['id']}: tier mismatch"
            assert row["category"] == q["category"], f"{arch_key}/{row['id']}: category mismatch"


_run_startup_checks()


def _compute_comparison_table() -> pd.DataFrame:
    rows = []
    for arch_key, info in ARCHS.items():
        subset = RESULTS[RESULTS["arch"] == arch_key]
        row = {"Architecture": info["label"]}

        overall_correct = subset["correct"].sum()
        overall_total = len(subset)
        row["Overall"] = f"{overall_correct / overall_total:.0%} ({overall_correct}/{overall_total})"

        for tier in sorted(subset["tier"].unique()):
            tier_subset = subset[subset["tier"] == tier]
            correct = tier_subset["correct"].sum()
            total = len(tier_subset)
            row[f"T{tier}"] = f"{correct / total:.0%} ({correct}/{total})"

        rows.append(row)
    return pd.DataFrame(rows)


COMPARISON_TABLE = _compute_comparison_table()


def _format_question_label(q: dict) -> str:
    text = q["question"]
    if len(text) > 60:
        text = text[:57] + "..."
    return f"{q['id']} · T{q['tier']} · {text}"


def _question_choices(tier_filter: str, disagreements_only: bool) -> list[str]:
    ids = sorted(QUESTIONS.keys())

    if tier_filter != "All":
        tier_num = tier_filter.replace("T", "")
        ids = [qid for qid in ids if str(QUESTIONS[qid]["tier"]) == tier_num]

    if disagreements_only:
        disagreeing = set()
        for qid in ids:
            correctness = RESULTS[RESULTS["id"] == qid]["correct"]
            if correctness.nunique() > 1:
                disagreeing.add(qid)
        ids = [qid for qid in ids if qid in disagreeing]

    return [_format_question_label(QUESTIONS[qid]) for qid in ids]


def _label_to_id(label: str) -> str:
    return label.split(" · ")[0]


def _int_or_zero(value) -> int:
    return int(value) if pd.notna(value) else 0


def _format_cost(arch_key: str, row: pd.Series) -> str:
    cost = float(row["cost"])
    retries_used = _int_or_zero(row.get("retries_used", 0))

    if arch_key == "local_baseline" or arch_key == "local_routed":
        return "$0 (local inference)"

    if arch_key == "hosted_baseline":
        return "replayed from cache, not re-billed (full-run spend ≈ $0.01, per DECISIONS.md)"

    # hosted_routed
    if cost == 0:
        return "replayed from cache, not re-billed"
    if retries_used == 0:
        return f"${cost:.5f}"
    return f"${cost:.5f} (billed in this run - attempt 1 may have been a cache replay, not included)"


def _format_latency(arch_key: str, row: pd.Series) -> str:
    latency_ms = float(row["llm_latency_ms"])
    is_agent = arch_key in ("local_routed", "hosted_routed")
    retries_used = _int_or_zero(row.get("retries_used")) if is_agent else 0

    if retries_used == 0:
        return f"{latency_ms:.0f}ms (model-call time, as originally measured)"

    n_attempts = retries_used + 1
    return (
        f"{latency_ms:.0f}ms total across {n_attempts} attempts "
        f"(attempt 1 may be an earlier measurement replayed from cache)"
    )


def get_answer(question_id: str, arch_key: str) -> dict:
    row = RESULTS[(RESULTS["id"] == question_id) & (RESULTS["arch"] == arch_key)].iloc[0]
    q = QUESTIONS[question_id]
    is_agent = arch_key in ("local_routed", "hosted_routed")

    return {
        "question": q["question"],
        "tier": q["tier"],
        "category": q["category"],
        "ordered": q.get("ordered", False),
        "ground_truth_sql": q["sql"],
        "generated_sql": row["generated_sql"],
        "correct": bool(row["correct"]),
        "error": row["error"] if pd.notna(row["error"]) else None,
        "route": row["route"] if is_agent and pd.notna(row.get("route")) else None,
        "retries_used": int(row["retries_used"]) if is_agent and pd.notna(row.get("retries_used")) else None,
        "retrieved_tables": row["initial_retrieved_tables"] if is_agent and pd.notna(row.get("initial_retrieved_tables")) else None,
        "cost_display": _format_cost(arch_key, row),
        "latency_display": _format_latency(arch_key, row),
    }


ARCH_LABELS = {info["label"]: key for key, info in ARCHS.items()}


def _all_arch_strip(question_id: str) -> pd.DataFrame:
    rows = []
    for key, info in ARCHS.items():
        match = RESULTS[(RESULTS["id"] == question_id) & (RESULTS["arch"] == key)]
        ok = bool(match.iloc[0]["correct"])
        rows.append({
            "Architecture": info["label"],
            "Result": "✅ correct" if ok else "❌ incorrect",
        })
    return pd.DataFrame(rows)


def render_answer(question_label: str | None, arch_label: str):
    if not question_label:
        return "No question matches these filters.", "", "", "", "", pd.DataFrame()

    qid = _label_to_id(question_label)
    arch_key = ARCH_LABELS[arch_label]
    a = get_answer(qid, arch_key)

    header = f"### {qid} · Tier {a['tier']} · {a['category']}\n\n{a['question']}"

    status = "✅ **Correct**" if a["correct"] else "❌ **Incorrect**"
    if a["error"]:
        status += f"\n\nDuckDB error:\n```\n{a['error']}\n```"

    lines = [f"- Row order matters for this question: {'yes' if a['ordered'] else 'no'}"]

    if a["route"] is not None:
        lines.append(f"- Route: {a['route']}")
        lines.append(f"- Retries used: {a['retries_used']}")
        lines.append(f"- Tables retrieved (first pass): {a['retrieved_tables']}")
    lines.append(f"- Cost: {a['cost_display']}")
    lines.append(f"- Latency: {a['latency_display']}")
    details = "\n".join(lines)

    return header, a["ground_truth_sql"], a["generated_sql"], status, details, _all_arch_strip(qid)


def spend_line() -> str:
    hosted_routed = RESULTS[RESULTS["arch"] == "hosted_routed"]["cost"].sum()
    return (
        "**Spend:** local runs cost $0. The hosted baseline cost about $0.01 per 100 questions "
        "(its CSV shows $0 because every call was a cache replay; figure from the project's DECISIONS.md). "
        f"The hosted routed agent billed ${hosted_routed:.3f} in its run, with cache hits excluded."
    )


TIER_CHOICES = ["All", "T1", "T2", "T3", "T4", "T5"]
DEFAULT_QUESTION_ID = "q040"
DEFAULT_ARCH = ARCHS["local_routed"]["label"]


def _refresh_choices(tier_filter, disagreements_only):
    choices = _question_choices(tier_filter, disagreements_only)
    return gr.Dropdown(choices=choices, value=choices[0] if choices else None)


_initial_choices = _question_choices("All", False)
_initial_value = _format_question_label(QUESTIONS[DEFAULT_QUESTION_ID])

with gr.Blocks(title="Text2SQL Agent Eval") as demo:
    gr.Markdown(
        "# text2sql-agent-eval: results explorer\n\n"
        "100 questions over an Olist e-commerce warehouse, 5 difficulty tiers, "
        "4 architectures. This is a replay of committed results; nothing runs live."
    )

    gr.Markdown("## Comparison")
    gr.DataFrame(value=COMPARISON_TABLE, interactive=False)
    gr.Markdown(spend_line())
    gr.Markdown(
        "Single runs. Retry temperature (0.4) and hosted API calls both add "
        "run-to-run variance, so read these as accuracy ± a few points."
    )

    gr.Markdown("## Question explorer")
    with gr.Row():
        tier_radio = gr.Radio(TIER_CHOICES, value="All", label="Tier")
        disagree_box = gr.Checkbox(label="Only questions where architectures disagree")
    with gr.Row():
        question_dd = gr.Dropdown(
            choices=_initial_choices,
            value=_initial_value,
            label="Question (type an id or words from the question)",
            filterable=True,
        )
        arch_radio = gr.Radio(list(ARCH_LABELS), value=DEFAULT_ARCH, label="Architecture")

    header_md = gr.Markdown()
    with gr.Row():
        gt_code = gr.Code(label="Ground-truth SQL", language="sql")
        gen_code = gr.Code(label="Generated SQL", language="sql")
    status_md = gr.Markdown()
    details_md = gr.Markdown()
    strip_df = gr.Dataframe(label="All four architectures on this question", interactive=False)

    with gr.Accordion("How correctness is judged", open=False):
        gr.Markdown(
            "Correct means the **result set** matches the ground truth, not the SQL text. "
            "Column names and column order are ignored. Numbers match within an absolute "
            "tolerance of 0.01. Row order only matters when the question asks for an order. "
            "NULL matches NULL. So a query that looks different from the ground truth can "
            "still be marked correct."
        )

    outputs = [header_md, gt_code, gen_code, status_md, details_md, strip_df]
    tier_radio.change(_refresh_choices, [tier_radio, disagree_box], question_dd)
    disagree_box.change(_refresh_choices, [tier_radio, disagree_box], question_dd)
    question_dd.change(render_answer, [question_dd, arch_radio], outputs)
    arch_radio.change(render_answer, [question_dd, arch_radio], outputs)
    demo.load(render_answer, [question_dd, arch_radio], outputs)


if __name__ == "__main__":
    demo.launch()