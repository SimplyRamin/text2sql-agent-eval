from src.graph.run import build_initial_state
from src.graph.graph import build_graph
from evals.scorer import load_questions

questions = {q["id"]: q for q in load_questions()}
graph = build_graph()

for qid in ["q013", "q027"]:
    initial_state = build_initial_state(questions[qid], "gpt-4o-mini", "hosted")
    final_state = graph.invoke(initial_state)
    print(qid, "| correct:", final_state["correct"], "| sql:", final_state["sql"])
