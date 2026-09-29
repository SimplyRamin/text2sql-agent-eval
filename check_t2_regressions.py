import csv

def load(path):
    with open(path, newline="", encoding="utf-8") as f:
        return {r["id"]: r for r in csv.DictReader(f)}

baseline = load("results/baseline_gpt-4o-mini_20260929_102108.csv")
routed = load("results/agent_gpt-4o-mini_20260929_102707.csv")

for qid, b in baseline.items():
    r = routed.get(qid)
    if r and b["tier"] == "2" and b["correct"] == "True" and r["correct"] == "False":
        print(qid, "| route:", r["route"], "| error:", (r["error"] or "")[:100])
