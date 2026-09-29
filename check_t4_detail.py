import csv
from evals.scorer import load_questions

def load_row(path, qid):
    with open(path, newline="", encoding="utf-8") as f:
        rows = {r["id"]: r for r in csv.DictReader(f)}
    return rows[qid]

questions = {q["id"]: q for q in load_questions()}

for qid in ["q064", "q069", "q073", "q076", "q079"]:
    row = load_row("results/baseline_gpt-4o-mini_20260927_154700.csv", qid)
    print(qid, "| question:", questions[qid]["question"])
    print("  ground truth:", questions[qid]["sql"])
    print("  generated:", row["generated_sql"])
    print()
