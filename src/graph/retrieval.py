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

    return retrieved