# =================================================================================================
#                                           Written by Ramin F.
#                                           Senior AI Engineer
#                            Ferdos.ramin@gmail.com | simplyramin.github.io
# =================================================================================================

from evals.scorer import score_question
from src import llm
from src.baseline import TABLES, build_prompt, build_schema_string, extract_sql
from src.graph import prompts, retrieval
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


def classify_complexity(state: GraphState) -> dict:
    groups = retrieval.count_entity_groups(state["retrieved_tables"])
    route = "join" if groups >= 3 else "simple"
    return {"route": route}


def generate_sql_simple(state: GraphState) -> dict:
    if state["retry_count"] == 0:
        prompt = build_prompt(state["schema_context"], state["question"]["question"])
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

    if "category_translation" in state["retrieved_tables"]:
        prompt += f"\n{prompts.CATEGORY_NAME_NOTE}\n"

    temperature = 0.0 if state["retry_count"] == 0 else 0.4
    return _call_llm_and_record(state, prompt, temperature)


def generate_sql_join(state: GraphState) -> dict:
    if state["retry_count"] == 0:
        prompt = prompts.build_join_prompt(
            state["schema_context"], state["question"]["question"], state["retrieved_tables"]
        )
    else:
        error_message = state["error"] or (
            "The query executed without a database error, but the result did "
            "not correctly answer the question. Reconsider your table choice, "
            "joins, filters, and aggregation logic."
        )
        prompt = prompts.build_join_retry_prompt(
            state["schema_context"],
            state["question"]["question"],
            state["sql"],
            error_message,
            state["retrieved_tables"],
        )

    if "category_translation" in state["retrieved_tables"]:
        prompt += f"\n{prompts.CATEGORY_NAME_NOTE}\n"

    temperature = 0.0 if state["retry_count"] == 0 else 0.4
    return _call_llm_and_record(state, prompt, temperature)


def _call_llm_and_record(state: GraphState, prompt: str, temperature: float) -> dict:
    attempt_number = state["retry_count"] + 1

    try:
        response = llm.complete(prompt, model=state["model"], provider=state["provider"], temperature=temperature)
    except Exception as e:
        return {
            "sql": "",
            "correct": False,
            "error": f"LLM call failed: {e}",
            "retry_count": attempt_number,
        }

    usage = response["usage"]
    return {
        "sql": extract_sql(response["text"]),
        "retry_count": attempt_number,
        "total_cost": state["total_cost"] + response["cost"],
        "total_in_tokens": state["total_in_tokens"] + usage["in_tokens"],
        "total_out_tokens": state["total_out_tokens"] + usage["out_tokens"],
        "total_llm_latency_ms": state["total_llm_latency_ms"] + response["latency_ms"],
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