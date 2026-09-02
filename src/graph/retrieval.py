# =================================================================================================
#                                           Written by Ramin F.
#                                           Senior AI Engineer
#                            Ferdos.ramin@gmail.com | simplyramin.github.io
# =================================================================================================

import re

from src.baseline import TABLES as ALL_TABLES

KEYWORD_TABLES: dict[tuple[str, ...], list[str]] = {
    ("orders", "stg_orders"): [
        "order", "orders", "status", "purchase", "approved", "delivered",
        "delivery", "estimated", "carrier", "canceled", "cancelled",
        "shipped", "late", "delay", "on time",
    ],
    ("customers", "stg_customers"): [
        "customer", "customers", "city", "state", "zip", "unique id",
    ],
    ("order_items",): [
        "item", "items", "price", "freight", "line item",
    ],
    ("order_payments",): [
        "payment", "payments", "paid", "installment", "boleto", "voucher",
        "credit card", "debit card",
    ],
    ("order_reviews",): [
        "review", "reviews", "score", "rating", "comment",
    ],
    ("products", "category_translation"): [
        "product", "products", "category", "weight", "dimension", "photo",
    ],
    ("sellers",): [
        "seller", "sellers",
    ],
    ("geolocation",): [
        "geolocation", "latitude", "longitude", "lat", "lng", "coordinate",
        "distance",
    ],
}

ORDER_BRIDGE_GROUPS = [
    ("order_items",),
    ("order_payments",),
    ("order_reviews",),
]


def _add_order_bridge(retrieved: list[str]) -> list[str]:
    retrieved_set = set(retrieved)
    has_customers = "customers" in retrieved_set or "stg_customers" in retrieved_set
    has_order_child = any(
        retrieved_set & set(group) for group in ORDER_BRIDGE_GROUPS
    )
    if has_customers and has_order_child and "orders" not in retrieved_set:
        return retrieved + ["orders", "stg_orders"]
    return retrieved


def _keyword_matches(keyword: str, text: str) -> bool:
    if " " in keyword:
        return keyword in text
    return re.search(rf"\b{re.escape(keyword)}(\b|_)", text) is not None


def retrieve_tables(question_text: str) -> list[str]:
    text = question_text.lower()
    retrieved: list[str] = []

    for tables, keywords in KEYWORD_TABLES.items():
        if any(_keyword_matches(kw, text) for kw in keywords):
            retrieved.extend(tables)

    if not retrieved:
        return ALL_TABLES

    return _add_order_bridge(retrieved)


def count_entity_groups(retrieved_tables: list[str]) -> int:
    retrieved_set = set(retrieved_tables)
    return sum(1 for tables in KEYWORD_TABLES if retrieved_set & set(tables))