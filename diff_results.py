import csv

def load(path):
    with open(path) as f:
        return {row['id']: row for row in csv.DictReader(f)}

baseline = load('results/baseline_qwen2.5-coder-7b_20260825_154930.csv')
agent = load('results/agent_qwen2.5-coder-7b_20260831_154230.csv')

regressions = []
improvements = []
for qid in baseline:
    b_correct = baseline[qid]['correct'] == 'True'
    a_correct = agent[qid]['correct'] == 'True'
    if b_correct and not a_correct:
        regressions.append((qid, agent[qid]['tier'], agent[qid]['initial_retrieved_tables']))
    elif not b_correct and a_correct:
        improvements.append((qid, agent[qid]['tier'], agent[qid]['retries_used']))

print(f'Regressions ({len(regressions)}):')
for r in regressions:
    print(' ', r)
print(f'Improvements ({len(improvements)}):')
for i in improvements:
    print(' ', i)
