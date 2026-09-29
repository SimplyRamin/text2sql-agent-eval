# =================================================================================================
#                                           Written by Ramin F.
#                                           Senior AI Engineer
#                            Ferdos.ramin@gmail.com | simplyramin.github.io
# =================================================================================================

import math
from pathlib import Path

import duckdb
import yaml

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "olist.db"
QUESTIONS_PATH = Path(__file__).resolve().parent / "questions.yaml"


def run_query(sql: str) -> list[tuple]:
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        return con.sql(sql).fetchall()
    finally:
        con.close()


def _sort_key(value):
    """
    Type-safe sort key - groups by type first so a row mixing e.g. a
    string and a float never crashes Python's comparison (you can't do
    'abc' < 3.0 directly).
    """
    if value is None:
        return (0, "")
    if isinstance(value, (int, float)):
        return (1, float(value))
    return (2, str(value))


def _values_equal(a, b) -> bool:
    if a is None or b is None:
        return a is None and b is None
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(a, b, rel_tol=1e-4, abs_tol=0.01)
    return a == b


def _normalize_row(row: tuple) -> list:
    return sorted(row, key=_sort_key)


def _rows_match(row_a: tuple, row_b: tuple) -> bool:
    norm_a = _normalize_row(row_a)
    norm_b = _normalize_row(row_b)
    if len(norm_a) != len(norm_b):
        return False
    return all(_values_equal(a, b) for a, b in zip(norm_a, norm_b))


def compare_results(expected: list[tuple], actual: list[tuple], ordered: bool) -> bool:
    if len(expected) != len(actual):
        return False

    if ordered:
        return all(_rows_match(e, a) for e, a in zip(expected, actual))

    # Unordered: greedily match each expected row against an unused actual
    # row. Needed instead of just sorting both lists and zipping, because
    # rows can repeat (e.g. two states tied at the same count) - a multiset
    # comparison, not a positional one.
    remaining = list(actual)
    for expected_row in expected:
        match_index = next(
            (i for i, actual_row in enumerate(remaining) if _rows_match(expected_row, actual_row)),
            None,
        )
        if match_index is None:
            return False
        remaining.pop(match_index)
    return True


def load_questions() -> list[dict]:
    with open(QUESTIONS_PATH) as f:
        return yaml.safe_load(f)


def score_question(question: dict, agent_sql: str) -> dict:
    expected = run_query(question["sql"])

    try:
        actual = run_query(agent_sql)
    except Exception as e:
        return {"id": question["id"], "correct": False, "error": str(e)}

    correct = compare_results(expected, actual, question.get("ordered", False))
    return {"id": question["id"], "correct": correct, "error": None}