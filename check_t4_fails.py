import csv

def load_fails(path):
    with open(path, newline="", encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if r["tier"] == "4" and r["correct"] == "False"]

for path in [
    "results/baseline_gpt-4o-mini_20260927_154700.csv",
    "results/agent_gpt-4o-mini_20260927_155849.csv",
]:
    print(f"--- {path} ---")
    for r in load_fails(path):
        print(r["id"], "| error:", (r["error"] or "")[:80])
    print()
