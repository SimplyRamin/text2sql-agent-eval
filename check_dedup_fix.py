import csv

with open('results/agent_qwen2.5-coder-7b_20260902_120509.csv') as f:
    rows = {row['id']: row for row in csv.DictReader(f)}

for qid in ['q086', 'q090']:
    r = rows[qid]
    print(qid, '| error:', r['error'])
    print('  sql:', r['generated_sql'])
    print()
