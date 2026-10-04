# =================================================================================================
#                                           Written by Ramin F.
#                                           Senior AI Engineer
#                            Ferdos.ramin@gmail.com | simplyramin.github.io
# =================================================================================================

import csv
import hashlib
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPACE = ROOT / "demo" / "_space"

# (path in this repo, path inside the Space)
FILES = [
    ("demo/README.md", "README.md"),
    ("demo/requirements.txt", "requirements.txt"),
    ("demo/app.py", "demo/app.py"),
    ("evals/questions.yaml", "evals/questions.yaml"),
    ("results/baseline_qwen2.5-coder-7b_20260929_105034.csv",
     "results/baseline_qwen2.5-coder-7b_20260929_105034.csv"),
    ("results/agent_qwen2.5-coder-7b_20260929_111951.csv",
     "results/agent_qwen2.5-coder-7b_20260929_111951.csv"),
    ("results/baseline_gpt-4o-mini_20260929_103950.csv",
     "results/baseline_gpt-4o-mini_20260929_103950.csv"),
    ("results/agent_gpt-4o-mini_20260929_105023.csv",
     "results/agent_gpt-4o-mini_20260929_105023.csv"),
]

EXPECTED_CORRECT = {
    "results/baseline_qwen2.5-coder-7b_20260929_105034.csv": 66,
    "results/agent_qwen2.5-coder-7b_20260929_111951.csv": 69,
    "results/baseline_gpt-4o-mini_20260929_103950.csv": 79,
    "results/agent_gpt-4o-mini_20260929_105023.csv": 84,
}


def main():
    missing = [src for src, _ in FILES if not (ROOT / src).exists()]
    if missing:
        raise SystemExit(f"Missing files: {missing}")

    if SPACE.exists():
        shutil.rmtree(SPACE)

    for src, dest in FILES:
        target = SPACE / dest
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / src, target)

    for src, expected in EXPECTED_CORRECT.items():
        with open(ROOT / src, newline="", encoding="utf-8") as f:
            correct = sum(1 for row in csv.DictReader(f) if row["correct"] == "True")
        if correct != expected:
            raise SystemExit(f"{src}: expected {expected} correct, found {correct}")
        digest = hashlib.sha256((ROOT / src).read_bytes()).hexdigest()
        print(f"{correct}/100   sha256={digest[:12]}    {src}")

    print(f"\nSpace snapshot built at {SPACE}")


if __name__ == "__main__":
    main()