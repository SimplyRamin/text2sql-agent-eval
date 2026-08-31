# =================================================================================================
#                                           Written by Ramin F.
#                                   for Tabiat Makan Industrial Group
# =================================================================================================

from typing import TypedDict


class GraphState(TypedDict):
    question: dict
    model: str
    schema_context: str
    retrieved_tables: list[str]
    initial_retrieved_tables: list[str]
    sql: str
    correct: bool
    error: str | None
    retry_count: int


MAX_RETRIES = 2
MAX_ATTEMPTS = MAX_RETRIES + 1