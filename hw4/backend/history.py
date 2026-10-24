"""Saved chat history for signed-in customers, stored in the existing `chat_messages` table.

Table (unchanged): id, user_id -> users.id, role ('user' | 'assistant'), content,
products_json (assistant rows only), created_at (filled in by the database).

`products_json` keeps the same shape as the rows that were already in the table: a JSON
list of product objects. Each saved item also records how it was shown:
    {"product_id", "name", "price", "image_url", "shown_as": "chat_card" | "page_result" | "context",
     "page_query", "page_total"}   (the last two only on page results)
"context" items (Problem 9) aren't shown; they record which product a follow-up question
("Does it come in blue?") refers to, when the reply had no product card for it.
When history is reloaded, cards are rebuilt from the *current* catalogue, so prices
and stock are never stale.

Guests' chats are never saved. Only the signed-in customer's own rows are ever read.
"""

from __future__ import annotations

import json

from db import connect
from models import ChatTurn, PageResults, ProductCard

HISTORY_FOR_AGENT = 20  # earlier messages given to the AI as context
HISTORY_FOR_WINDOW = 50  # earlier messages shown when the chat window reopens


def recent_turns(user_id: int, limit: int = HISTORY_FOR_AGENT) -> list[ChatTurn]:
    """The customer's latest saved messages, oldest first, as context for the agent."""
    with connect() as conn:
        rows = conn.execute(
            "SELECT role, content FROM chat_messages WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user_id, limit)
        ).fetchall()
    return [ChatTurn(role=r["role"], content=r["content"][:4000]) for r in reversed(rows) if r["role"] in ("user", "assistant")]


def saved_rows(user_id: int, limit: int = HISTORY_FOR_WINDOW) -> list[dict]:
    """The customer's latest saved messages with their stored products, oldest first."""
    with connect() as conn:
        rows = conn.execute(
            "SELECT role, content, products_json, created_at FROM chat_messages WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    out = []
    for r in reversed(rows):
        if r["role"] not in ("user", "assistant"):
            continue
        try:
            items = json.loads(r["products_json"]) if r["products_json"] else []
        except ValueError:
            items = []
        out.append({"role": r["role"], "content": r["content"], "created_at": r["created_at"], "items": items if isinstance(items, list) else []})
    return out


def last_discussed_ids(user_id: int) -> list[str]:
    """Problem 9: the product(s) the customer's latest saved assistant reply was about (its cards or context)."""
    with connect() as conn:
        row = conn.execute(
            "SELECT products_json FROM chat_messages WHERE user_id = ? AND role = 'assistant' ORDER BY id DESC LIMIT 1", (user_id,)
        ).fetchone()
    try:
        items = json.loads(row["products_json"]) if row and row["products_json"] else []
    except ValueError:
        return []
    if not isinstance(items, list):
        return []
    ids = [i["product_id"] for i in items
           if isinstance(i, dict) and isinstance(i.get("product_id"), str) and i.get("shown_as", "chat_card") in ("chat_card", "context")]
    return list(dict.fromkeys(ids))[:3]


def save_exchange(
    user_id: int, message: str, reply: str, cards: list[ProductCard], page_results: PageResults | None,
    context_ids: list[str] | None = None,
) -> None:
    """Save the customer's message and the assistant's reply together (one transaction)."""
    items = [
        {"product_id": c.product_id, "name": c.name, "price": c.price, "image_url": c.image_url, "shown_as": "chat_card"}
        for c in cards
    ]
    card_ids = {c.product_id for c in cards}
    items += [{"product_id": pid, "shown_as": "context"} for pid in (context_ids or []) if pid not in card_ids]
    if page_results is not None and page_results.total > 0:
        items += [
            {
                "product_id": p.product_id, "name": p.name, "price": p.price, "image_url": p.image_url,
                "shown_as": "page_result", "page_query": page_results.query, "page_total": page_results.total,
            }
            for p in page_results.products
        ]
    with connect(write=True) as conn, conn:
        conn.execute("INSERT INTO chat_messages (user_id, role, content) VALUES (?, 'user', ?)", (user_id, message))
        conn.execute(
            "INSERT INTO chat_messages (user_id, role, content, products_json) VALUES (?, 'assistant', ?, ?)",
            (user_id, reply, json.dumps(items)),
        )
