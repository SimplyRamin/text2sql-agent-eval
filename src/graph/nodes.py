# =================================================================================================
#                                           Written by Ramin F.
#                                           Senior AI Engineer
#                            Ferdos.ramin@gmail.com | simplyramin.github.io
# =================================================================================================

from evals.scorer import score_question
from src import llm
from src.baseline import TABLES, build_prompt, build_schema_string, extract_sql
from src.graph.retrieval import retrieve_tables
from src.graph.state import GraphState


def retrieve_schema(state: GraphState) -> dict:
    if state["retry_count"] == 0:
        tables = retrieve_tables(state["question"]["question"]) or TABLES
        schema = build_schema_string(tables)
        return {
            "schema_context": schema,
            "retrieved_tables": tables,
            "initial_retrieved_tables": tables,
        }
    else:
        return {
            "schema_context": build_schema_string(TABLES),
            "retrieved_tables": TABLES,
        }


def build_retry_prompt(schema: str, question: str, previous_sql: str, error: str) -> str:
    return f"""You are a SQL expert working with a DuckDB database.

Given the following schema:

{schema}

You previously attempted to answer this question:
{question}

Your previous SQL query was:
{previous_sql}

That query failed with this error:
{error}

Write a corrected SQL query that answers the question. Return only the SQL
query. Do not include any explanation.
"""


def generate_sql(state: GraphState) -> dict:
    attempt_number = state["retry_count"] + 1

    if state["retry_count"] == 0:
        prompt = build_prompt(state["schema_context"], state["question"]["question"])
        temperature = 0.0
    else:
        error_message = state["error"] or (
            "The query executed without a database error, but the result did "
            "not correctly answer the question. Reconsider your table choice, "
            "joins, filters, and aggregation logic."
        )
        prompt = build_retry_prompt(
            state["schema_context"],
            state["question"]["question"],
            state["sql"],
            error_message,
        )
        temperature = 0.4

    try:
        response = llm.complete(prompt, model=state["model"], provider="local", temperature=temperature)
    except Exception as e:
        return {
            "sql": "",
            "correct": False,
            "error": f"LLM call failed: {e}",
            "retry_count": attempt_number,
        }

    return {"sql": extract_sql(response["text"]), "retry_count": attempt_number}


def execute_and_score(state: GraphState) -> dict:
    if not state["sql"]:
        return {}
    result = score_question(state["question"], state["sql"])
    return {"correct": result["correct"], "error": result["error"]}