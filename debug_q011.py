from src.graph.run import build_initial_state
from src.graph.graph import build_graph
from evals.scorer import load_questions

questions = load_questions()
q011 = next(q for q in questions if q['id'] == 'q011')

graph = build_graph()
initial_state = build_initial_state(q011, 'qwen2.5-coder:7b')

for step in graph.stream(initial_state):
    node_name, update = next(iter(step.items()))
    print(f'=== after {node_name} ===')
    for k, v in update.items():
        print(f'{k}: {v}')
    print()
