from src.graph.retrieval import retrieve_tables, count_entity_groups
from evals.scorer import load_questions

questions = load_questions()
for q in questions:
    tables = retrieve_tables(q['question'])
    groups = count_entity_groups(tables)
    print(q['id'], q['tier'], groups, sorted(tables))
