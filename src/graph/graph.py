# =================================================================================================
#                                           Written by Ramin F.
#                                           Senior AI Engineer
#                            Ferdos.ramin@gmail.com | simplyramin.github.io
# =================================================================================================

from typing import Literal

from langgraph.graph import END, START, StateGraph

from src.graph.nodes import (
    classify_complexity,
    execute_and_score,
    generate_sql_join,
    generate_sql_simple,
    retrieve_schema,
)
from src.graph.state import MAX_ATTEMPTS, GraphState


def route_after_score(state: GraphState) -> Literal["retry", "done"]:
    if state["correct"]:
        return "done"
    if state["retry_count"] >= MAX_ATTEMPTS:
        return "done"
    return "retry"


def build_graph():
    graph = StateGraph(GraphState)

    graph.add_node("retrieve_schema", retrieve_schema)
    graph.add_node("classify_complexity", classify_complexity)
    graph.add_node("generate_sql_simple", generate_sql_simple)
    graph.add_node("generate_sql_join", generate_sql_join)
    graph.add_node("execute_and_score", execute_and_score)

    graph.add_edge(START, "retrieve_schema")
    graph.add_edge("retrieve_schema", "classify_complexity")

    graph.add_conditional_edges(
        "classify_complexity",
        lambda state: state["route"],
        {"simple": "generate_sql_simple", "join": "generate_sql_join"},
    )

    graph.add_edge("generate_sql_simple", "execute_and_score")
    graph.add_edge("generate_sql_join", "execute_and_score")

    graph.add_conditional_edges(
        "execute_and_score",
        route_after_score,
        {"retry": "retrieve_schema", "done": END}
    )

    return graph.compile()