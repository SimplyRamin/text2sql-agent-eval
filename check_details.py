import csv
from evals.scorer import load_questions

with open('results/agent_qwen2.5-coder-7b_20260902_103420.csv') as f:
    rows = {row['id']: row for row in csv.DictReader(f)}

questions = {q['id']: q for q in load_questions()}

for qid in ['q013', 'q019']:
    print(qid, '| question:', questions[qid]['question'])
    print('  ground truth:', questions[qid]['sql'])
    print('  generated:', rows[qid]['generated_sql'])
    print()
