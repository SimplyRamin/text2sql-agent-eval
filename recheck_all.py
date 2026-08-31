from src.graph.retrieval import retrieve_tables
from evals.scorer import load_questions

questions = load_questions()
for q in questions:
    tables = retrieve_tables(q['question'])
    print(q['id'], sorted(tables))
