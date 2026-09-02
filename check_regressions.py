import csv

with open('results/agent_qwen2.5-coder-7b_20260902_112443.csv') as f:
    rows = {row['id']: row for row in csv.DictReader(f)}

for qid in ['q086', 'q090', 'q064']:
    r = rows[qid]
    print(qid, '| route:', r['route'], '| error:', r['error'])
    print('  sql:', r['generated_sql'])
    print()
