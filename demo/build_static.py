# =================================================================================================
#                                           Written by Ramin F.
#                                           Senior AI Engineer
#                            Ferdos.ramin@gmail.com | simplyramin.github.io
# =================================================================================================
import json
from pathlib import Path

import app

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs"

EXPECTED_CORRECT = {
    "local_baseline": 66,
    "local_routed": 69,
    "hosted_baseline": 79,
    "hosted_routed": 84,
}


def _note(answer: dict) -> str:
    if answer["error"]:
        return answer["error"]
    if not answer["correct"]:
        return "The query ran without error but returned a different result than the ground truth."
    return ""


def build() -> dict:
    answers = {}
    questions = []
    for qid in sorted(app.QUESTIONS):
        per_arch = {}
        for arch_key in app.ARCHS:
            a = app.get_answer(qid, arch_key)
            a["note"] = _note(a)
            per_arch[arch_key] = a
        answers[qid] = per_arch
        questions.append({
            "id": qid,
            "tier": app.QUESTIONS[qid]["tier"],
            "label": app._format_question_label(app.QUESTIONS[qid]),
            "disagree": len({a["correct"] for a in per_arch.values()}) > 1,
        })

    return {
        "archs": [{"key": k, "label": v["label"]} for k, v in app.ARCHS.items()],
        "comparison": app.COMPARISON_TABLE.to_dict(orient="records"),
        "spend": app.spend_line().replace("**", ""),
        "questions": questions,
        "answers": answers,
    }


def main():
    for arch_key, expected in EXPECTED_CORRECT.items():
        found = int(app.RESULTS[app.RESULTS["arch"] == arch_key]["correct"].sum())
        assert found == expected, f"{arch_key}: expected {expected} correct, found {found}"

    data = build()
    OUT.mkdir(exist_ok=True)
    (OUT / "data.js").write_text("window.DATA = " + json.dumps(data) + ";\n", encoding="utf-8")
    (OUT / ".nojekyll").touch()

    print(app.COMPARISON_TABLE.to_string(index=False))
    print(f"\n{len(data['questions'])} questions, "
          f"{sum(q['disagree'] for q in data['questions'])} where architectures disagree")
    sample = data["answers"]["q040"]["hosted_routed"]
    print("q040 hosted_routed:", sample["cost_display"], "|", sample["latency_display"])
    print(f"Wrote {OUT / 'data.js'}")


if __name__ == "__main__":
    main()