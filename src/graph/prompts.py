# =================================================================================================
#                                           Written by Ramin F.
#                                           Senior AI Engineer
#                            Ferdos.ramin@gmail.com | simplyramin.github.io
# =================================================================================================

FK_HINTS: dict[tuple[str, str], str] = {
    ("orders", "customers"): "orders.customer_id = customers.customer_id",
    ("stg_orders", "stg_customers"): "stg_orders.customer_id = stg_customers.customer_id",
    ("order_items", "orders"): "order_items.order_id = orders.order_id",
    ("stg_order_items", "stg_orders"): "stg_order_items.order_id = stg_orders.order_id",
    ("order_items", "products"): "order_items.product_id = products.product_id",
    ("order_items", "sellers"): "order_items.seller_id = sellers.seller_id",
    ("order_payments", "orders"): "order_payments.order_id = orders.order_id",
    ("order_reviews", "orders"): "order_reviews.order_id = orders.order_id",
    ("products", "category_translation"): "products.product_category_name = category_translation.product_category_name",
}

DEDUP_CHECKLIST = (
    "If this query joins more than one table that has a many-to-one "
    "relationship with the same parent table (e.g. both order_payments "
    "and order_reviews joined to orders), use COUNT(DISTINCT ...) or a "
    "deduplicating subquery. A plain COUNT(*) or un-deduplicated AVG/SUM "
    "will double-count rows."
)

CATEGORY_NAME_NOTE = (
    "products.product_category_name already holds the category name used "
    "in this warehouse (e.g. informatica_acessorios). Only join "
    "category_translation and filter on product_category_name_english if "
    "the question explicitly asks for an English/translated category name."
)


def build_fk_hint_block(tables: list[str]) -> str:
    table_set = set(tables)
    hints = [
        hint
        for (table_a, table_b), hint in FK_HINTS.items()
        if table_a in table_set and table_b in table_set
    ]
    if not hints:
        return ""
    return "Known join keys:\n" + "\n".join(f"- {h}" for h in hints)


def build_join_prompt(schema: str, question: str, retrieved_tables: list[str]) -> str:
    fk_hint_block = build_fk_hint_block(retrieved_tables)
    fk_section = f"\n{fk_hint_block}\n" if fk_hint_block else ""

    return f"""You are a SQL expert working with a DuckDB database.

Given the following schema:

{schema}
{fk_section}
{DEDUP_CHECKLIST}

Write a SQL query to answer this question:
{question}

This question requires joining multiple tables. Before writing the final
query, briefly reason through the join path — which tables connect to
which, hop by hop, using the join keys above. Then write the SQL query in
a fenced ```sql code block.
"""


def build_join_retry_prompt(
        schema: str,
        question: str,
        previous_sql: str,
        error: str,
        retrieved_tables: list[str],
) -> str:
    fk_hint_block = build_fk_hint_block(retrieved_tables)
    fk_section = f"\n{fk_hint_block}\n" if fk_hint_block else ""

    return f"""You are a SQL expert working with a DuckDB database.

Given the following schema:

{schema}
{fk_section}
{DEDUP_CHECKLIST}

You previously attempted to answer this question:
{question}

Your previous SQL query was:
{previous_sql}

That query failed with this error:
{error}

Before writing a corrected query, briefly reason through the join path —
which tables connect to which, hop by hop, using the join keys above —
and check the query against the dedup guidance too. Then write the
corrected SQL query in a fenced ```sql code block.
"""