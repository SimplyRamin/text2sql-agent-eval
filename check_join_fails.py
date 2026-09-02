import csv

with open('results/agent_qwen2.5-coder-7b_20260902_103420.csv') as f:
    rows = {row['id']: row for row in csv.DictReader(f)}

for qid in ['q011', 'q013', 'q019']:
    r = rows[qid]
    print(qid, '| route:', r['route'], '| error:', r['error'][:100] if r['error'] else None)
    print('  sql:', r['generated_sql'][:200])
    print()
