from src.graph.run import build_initial_state
from src.graph.graph import build_graph
from evals.scorer import load_questions

questions = load_questions()
q001 = next(q for q in questions if q['id'] == 'q001')

graph = build_graph()
final_state = graph.invoke(build_initial_state(q001, 'qwen2.5-coder:7b'))

for key in ['route', 'total_cost', 'total_in_tokens', 'total_out_tokens', 'total_llm_latency_ms']:
    print(key, '=', final_state[key])
