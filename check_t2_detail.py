import csv
from evals.scorer import load_questions

def load(path):
    with open(path, newline="", encoding="utf-8") as f:
        return {r["id"]: r for r in csv.DictReader(f)}

baseline = load("results/baseline_gpt-4o-mini_20260929_102108.csv")
routed = load("results/agent_gpt-4o-mini_20260929_102707.csv")
questions = {q["id"]: q for q in load_questions()}

for qid in ["q013", "q021", "q025", "q027"]:
    print(qid, "| question:", questions[qid]["question"])
    print("  ground truth:", questions[qid]["sql"])
    print("  baseline (correct):", baseline[qid]["generated_sql"])
    print("  routed (wrong):", routed[qid]["generated_sql"])
    print()
