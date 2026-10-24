"""Campus Customs API: a small FastAPI backend for the shopping website.

Product endpoints open the database in SQLite read-only mode and use only the
`catalogue` and `inventory` tables. Customer accounts (register, log in, log out)
live in backend/auth.py; account registration is the only thing that writes to
the database. `chat_messages` is never read here.

The shopping-assistant chat (POST /api/chat) passes messages to the PydanticAI
agent in agent.py.

Run (from the backend/ folder):
    uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Annotated

from fastapi import Cookie, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pydantic_ai import capture_run_messages
from pydantic_ai.exceptions import ModelHTTPError

from agent import AssistantNotConfigured, ask_assistant, model_name
from audit import append_run, new_run_id, now, redact_reply, summarize_messages
from auth import router as auth_router
from auth import signed_in_user
from db import DATA_DIR
from db import connect as db
from history import last_discussed_ids, recent_turns, save_exchange, saved_rows
from models import ChatDeps, ChatHistory, ChatRequest, ChatResponse, DisplayProduct, HistoryMessage, PageResults, ProductCard
from tools import describe_page, find_products

log = logging.getLogger("campus_customs")

PRODUCTS_DIR = (DATA_DIR / "products").resolve()

# Sizes are stored as text; this is the order shoppers expect to see them in.
SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]


class SizeStock(BaseModel):
    size: str
    quantity: int
    in_stock: bool


class ProductSummary(BaseModel):
    product_id: str
    name: str
    garment_type: str
    description: str
    colors: list[str]
    search_tags: list[str]
    price: float
    image_url: str
    total_stock: int


class ProductDetail(ProductSummary):
    inventory: list[SizeStock]


class Inventory(BaseModel):
    product_id: str
    total_stock: int
    sizes: list[SizeStock]


def image_url(image_file_path: str) -> str:
    # The database stores paths like "products/basic-hoodie-big-yale.jpg" (relative to data/).
    return f"/api/images/{Path(image_file_path).name}"


def size_rows(conn: sqlite3.Connection, product_id: str) -> list[SizeStock]:
    rows = conn.execute("SELECT size, quantity FROM inventory WHERE product_id = ?", (product_id,)).fetchall()
    rank = {s: i for i, s in enumerate(SIZE_ORDER)}
    rows = sorted(rows, key=lambda r: rank.get(r["size"], len(SIZE_ORDER)))
    return [SizeStock(size=r["size"], quantity=r["quantity"], in_stock=r["quantity"] > 0) for r in rows]


def summary(row: sqlite3.Row) -> dict:
    return {
        "product_id": row["product_id"],
        "name": row["name"],
        "garment_type": row["garment_type"],
        "description": row["description"],
        "colors": json.loads(row["colors"]),
        "search_tags": json.loads(row["search_tags"]),
        "price": row["price"],
        "image_url": image_url(row["image_file_path"]),
        "total_stock": row["total_stock"],
    }


PRODUCT_QUERY = """
    SELECT c.*, COALESCE(SUM(i.quantity), 0) AS total_stock
    FROM catalogue AS c LEFT JOIN inventory AS i ON i.product_id = c.product_id
"""

app = FastAPI(title="Campus Customs API", version="1.1")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
    allow_credentials=True,  # lets the site send its sign-in cookie
)
app.include_router(auth_router)


@app.get("/api/health")
def health() -> dict:
    with db() as conn:
        count = conn.execute("SELECT COUNT(*) FROM catalogue").fetchone()[0]
    return {"status": "ok", "products": count}


@app.get("/api/products", response_model=list[ProductSummary])
def list_products(search: str | None = Query(None, max_length=100)) -> list[dict]:
    """All products, alphabetically. Optional `search` matches name, type, description, colors, and tags."""
    sql, params = PRODUCT_QUERY, []
    if search:
        like = f"%{search.strip()}%"
        sql += " WHERE c.name LIKE ? OR c.garment_type LIKE ? OR c.description LIKE ? OR c.colors LIKE ? OR c.search_tags LIKE ?"
        params = [like] * 5
    sql += " GROUP BY c.product_id ORDER BY c.name"
    with db() as conn:
        return [summary(r) for r in conn.execute(sql, params).fetchall()]


@app.get("/api/products/{product_id}", response_model=ProductDetail)
def product_detail(product_id: str) -> dict:
    with db() as conn:
        row = conn.execute(PRODUCT_QUERY + " WHERE c.product_id = ? GROUP BY c.product_id", (product_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Product not found")
        return {**summary(row), "inventory": size_rows(conn, product_id)}


@app.get("/api/products/{product_id}/inventory", response_model=Inventory)
def product_inventory(product_id: str) -> dict:
    with db() as conn:
        if conn.execute("SELECT 1 FROM catalogue WHERE product_id = ?", (product_id,)).fetchone() is None:
            raise HTTPException(status_code=404, detail="Product not found")
        sizes = size_rows(conn, product_id)
    return {"product_id": product_id, "total_stock": sum(s.quantity for s in sizes), "sizes": sizes}


# --- Shopping-assistant chat -------------------------------------------------------

CHAT_LIMIT_PER_MINUTE = 20
# Audit-trail labels for the ways an agent run can end early (anything else is "error: <type>").
STOP_REASONS = {
    "UsageLimitExceeded": "usage_limit_reached (too many model or tool calls)",
    "UnexpectedModelBehavior": "retries_exhausted (the model's answer kept failing validation)",
    "TimeoutError": "timeout",
    "APITimeoutError": "timeout",
    "ModelAPIError": "model_error",
}
_chat_requests: dict[str, deque[float]] = defaultdict(deque)
CHAT_UNAVAILABLE = "Sorry, the shopping assistant is having trouble right now. Please try again in a moment."
CONTENT_FILTERED = (
    "Sorry, I can't help with that request. I'm here to help you find Yale apparel and gifts at Campus Customs. "
    "What are you shopping for today?"
)


def _blocked_by_content_filter(exc: ModelHTTPError) -> bool:
    body = exc.body if isinstance(exc.body, dict) else {}
    error = body.get("error", body)
    code = error.get("code") if isinstance(error, dict) else None
    return exc.status_code == 400 and code in {"content_filter", "content_policy_violation"}


def _chat_rate_limited(client_ip: str) -> bool:
    now = time.time()
    recent = _chat_requests[client_ip]
    while recent and recent[0] < now - 60:
        recent.popleft()
    if len(recent) >= CHAT_LIMIT_PER_MINUTE:
        return True
    recent.append(now)
    return False


@app.post("/api/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, request: Request, cc_session: Annotated[str | None, Cookie()] = None) -> ChatResponse:
    """Send a customer's message to the shopping assistant and return its reply.

    Every request, whatever its outcome, adds one record to the audit trail (Problem 12; see audit.py).
    Message contents are never logged or audited. A signed-in customer's exchange is saved to
    their chat history (Problem 8).
    """
    run: dict = {"run_id": new_run_id(), "started_at": now(), "endpoint": "POST /api/chat", "model": model_name()}
    captured: list = []
    try:
        response = await _answer_chat(body, request, cc_session, run, captured)
        run["stop_reason"] = "final_answer" if run.get("stop_reason") is None else run["stop_reason"]
        return response
    except HTTPException as exc:
        run.setdefault("stop_reason", f"http_{exc.status_code}")
        run["http_status"] = exc.status_code
        raise
    except Exception as exc:  # noqa: BLE001 - recorded, then handled by FastAPI as before
        run.setdefault("stop_reason", f"error: {type(exc).__name__}")
        raise
    finally:
        run["finished_at"] = now()
        if captured:
            run.update(summarize_messages(captured, body.message.strip()))
        else:
            run.update({"model_requests": 0, "tool_calls": []})
        try:
            append_run(run)
        except OSError as exc:  # auditing must never break the chat
            log.warning("Could not write audit trail: %s", type(exc).__name__)


async def _answer_chat(body: ChatRequest, request: Request, cc_session: str | None, run: dict, captured: list) -> ChatResponse:
    if _chat_rate_limited(request.client.host if request.client else "?"):
        run["stop_reason"] = "rate_limited (agent not called)"
        raise HTTPException(429, "You're sending messages very quickly. Please wait a minute and try again.")
    user = signed_in_user(cc_session)
    deps = ChatDeps(
        customer_first_name=user.first_name if user else None,
        customer_last_name=user.last_name if user else None,
        customer_email=user.email if user else None,
        current_page=describe_page(body.page.path if body.page else None),
    )
    # Signed-in customers: the conversation comes from their saved history in the database, so it
    # can't be altered from the browser. Guests: the browser sends the (unsaved) conversation.
    turns = recent_turns(user.id) if user else body.history
    # Problem 9: which product(s) the last reply was about, so "Does it come in blue?" needs no product name.
    # Signed in: from the saved history. Guests: the ids the server sent with its last reply, checked here.
    if user:
        previous_ids = last_discussed_ids(user.id)
    else:
        last_reply = next((t for t in reversed(body.history) if t.role == "assistant"), None)
        previous_ids = last_reply.product_ids if last_reply else []
    deps.recent_products = _product_names(previous_ids)
    message = body.message.strip()
    # Audit: who (signed in or not, never the name), where, and how long the message was (never its text).
    run["customer"] = {"signed_in": user is not None, "page": body.page.path if body.page else None, "message_chars": len(message),
                       "earlier_turns_sent_to_ai": len(turns), "follow_up_context": [name for _pid, name in deps.recent_products]}
    with capture_run_messages() as messages:
        try:
            answer = await ask_assistant(message, turns, deps)
        except AssistantNotConfigured:
            run["stop_reason"] = "assistant_not_configured (no API key)"
            raise HTTPException(503, "The shopping assistant isn't available right now.") from None
        except ModelHTTPError as exc:
            if _blocked_by_content_filter(exc):
                # The AI provider's safety filter refused the message (e.g. a jailbreak attempt). That's an
                # answer, not an outage: reply politely instead of suggesting the customer try again.
                log.info("Chat message blocked by the provider's content filter")
                run["stop_reason"] = "content_filter_refusal (provider safety filter)"
                return ChatResponse(reply=CONTENT_FILTERED)
            log.warning("Chat request failed: %s %s", type(exc).__name__, exc.status_code)
            run["stop_reason"] = f"model_error: {type(exc).__name__} {exc.status_code}"
            raise HTTPException(502, CHAT_UNAVAILABLE) from None
        except Exception as exc:  # noqa: BLE001 - any AI/network failure becomes a friendly message
            log.warning("Chat request failed: %s", type(exc).__name__)  # error type only; never message text or keys
            run["stop_reason"] = STOP_REASONS.get(type(exc).__name__, f"error: {type(exc).__name__}")
            raise HTTPException(502, CHAT_UNAVAILABLE) from None
        finally:
            captured.extend(messages)
    if not answer.reply:
        run["stop_reason"] = "empty_reply"
        raise HTTPException(502, CHAT_UNAVAILABLE)
    page_results = None
    if answer.display_query is not None:  # already checked by the agent's validator: a real, good-quality search
        _quality, ids = deps.searches[answer.display_query]
        page_results = _page_results(answer.display_query, ids)
    elif deps.searches and all(quality in ("partial", "none") for quality, _ids in deps.searches.values()):
        # The customer searched but nothing really matched: tell the page, so it never keeps showing
        # earlier, unrelated results as if they answered this question.
        page_results = PageResults(query=list(deps.searches)[-1], total=0, products=[])
    cards = _product_cards(answer.product_ids)
    context_ids = _discussed_now(deps, cards, page_results)

    saved = False
    if user:
        try:
            save_exchange(user.id, message, answer.reply, cards, page_results, context_ids)
            saved = True
        except sqlite3.Error as exc:  # the customer still gets their answer; only saving failed
            log.warning("Could not save chat history: %s", type(exc).__name__)
    run["outcome"] = {
        "reply_chars": len(answer.reply),
        "reply_preview": redact_reply(answer.reply, [deps.customer_first_name or "", deps.customer_last_name or ""]),
        "product_cards": [c.name for c in cards],
        "page_results": None if page_results is None else {"query": page_results.query, "total": page_results.total},
        "saved_to_history": saved,
    }
    return ChatResponse(reply=answer.reply, products=cards, page_results=page_results, saved=saved, context_product_ids=context_ids)


def _product_names(product_ids: list[str]) -> list[tuple[str, str]]:
    """(product_id, name) for ids that are really in the catalogue, in the given order; anything else is dropped."""
    ids = [pid for pid in dict.fromkeys(product_ids) if isinstance(pid, str)][:3]
    if not ids:
        return []
    with db() as conn:
        names = dict(conn.execute(f"SELECT product_id, name FROM catalogue WHERE product_id IN ({','.join('?' * len(ids))})", ids).fetchall())
    return [(pid, names[pid]) for pid in ids if pid in names]


def _discussed_now(deps: ChatDeps, cards: list[ProductCard], page_results: PageResults | None) -> list[str]:
    """Problem 9: the product(s) this reply was about, for the next follow-up question.

    The reply's product cards if it has any; otherwise the one product it looked up; a single search
    result shown on the page; nothing if the customer moved on to a new search; else the same as before.
    """
    if cards:
        return [c.product_id for c in cards]
    looked_up = list(dict.fromkeys(deps.looked_up_ids))
    if len(looked_up) == 1:
        return looked_up
    if page_results is not None and page_results.total == 1:
        return [page_results.products[0].product_id]
    if deps.searches or looked_up:
        return []
    return [pid for pid, _name in deps.recent_products]


@app.get("/api/chat/history", response_model=ChatHistory)
def chat_history(cc_session: Annotated[str | None, Cookie()] = None) -> ChatHistory:
    """The signed-in customer's own saved conversation (latest 50 messages). Guests get an empty list."""
    user = signed_in_user(cc_session)
    if user is None:
        return ChatHistory(signed_in=False, messages=[])
    messages = []
    for row in saved_rows(user.id):
        items = [i for i in row["items"] if isinstance(i, dict) and i.get("product_id")]
        chat_ids = [i["product_id"] for i in items if i.get("shown_as", "chat_card") == "chat_card"][:3]
        page_items = [i for i in items if i.get("shown_as") == "page_result"]
        page = None
        if page_items:
            # Rebuilt from the current catalogue, so reloaded prices and stock are never out of date.
            page = _page_results(str(page_items[0].get("page_query", "earlier search")), [i["product_id"] for i in page_items])
            page.total = int(page_items[0].get("page_total", page.total))
        messages.append(
            HistoryMessage(
                role=row["role"], content=row["content"], created_at=row["created_at"],
                products=_product_cards(chat_ids) if row["role"] == "assistant" else [], page_results=page,
            )
        )
    return ChatHistory(signed_in=True, messages=messages)


MAX_PAGE_RESULTS = 30


@app.get("/api/search", response_model=PageResults)
def search(q: str = Query(..., min_length=1, max_length=120)) -> PageResults:
    """Problem 9: re-run an assistant search, so its results survive a page refresh or a shared link.

    Uses exactly the same search as the shopping assistant (tools.find_products) and the same rule for
    what may be shown: only good matches ("exact name", "strong", or "suggestions" for vague requests).
    Anything weaker returns total=0, and the page shows its "no matching products" message.
    """
    query = q.strip()[:120]
    outcome = find_products(query)
    if outcome.quality not in ("exact name", "strong", "suggestions"):
        return PageResults(query=query, total=0, products=[])
    return _page_results(query, outcome.product_ids)


def _page_results(query: str, product_ids: list[str]) -> PageResults:
    """Turn a search's matching ids into full product cards, read fresh from the database, in search order."""
    ids = product_ids[:MAX_PAGE_RESULTS]
    with db() as conn:
        rows = {
            r["product_id"]: r
            for r in conn.execute(
                PRODUCT_QUERY + f" WHERE c.product_id IN ({','.join('?' * len(ids))}) GROUP BY c.product_id", ids
            )
        }
        sizes = {pid: [s.size for s in size_rows(conn, pid) if s.in_stock] for pid in rows}
    products = []
    for pid in ids:
        if pid not in rows:
            continue
        card = summary(rows[pid])
        description = card["description"]
        products.append(
            DisplayProduct(
                **card,
                short_description=description if len(description) <= 160 else description[:159].rsplit(" ", 1)[0] + "…",
                sizes_in_stock=sizes[pid],
                url=f"/products/{pid}",
            )
        )
    return PageResults(query=query, total=len(product_ids), products=products)


def _product_cards(product_ids: list[str]) -> list[ProductCard]:
    """Build cards straight from the database, for ids the agent's tools already returned."""
    if not product_ids:
        return []
    with db() as conn:
        rows = {
            r["product_id"]: r
            for r in conn.execute(
                f"SELECT product_id, name, price, image_file_path FROM catalogue WHERE product_id IN ({','.join('?' * len(product_ids))})",
                product_ids,
            )
        }
    return [
        ProductCard(
            product_id=pid,
            name=rows[pid]["name"],
            price=rows[pid]["price"],
            image_url=image_url(rows[pid]["image_file_path"]),
            url=f"/products/{pid}",
        )
        for pid in product_ids
        if pid in rows
    ]


@app.get("/api/images/{filename}")
def product_image(filename: str) -> FileResponse:
    """Serve a product photo, but only one that the catalogue actually lists."""
    with db() as conn:
        row = conn.execute("SELECT image_file_path FROM catalogue WHERE image_file_path = ?", (f"products/{filename}",)).fetchone()
    path = (DATA_DIR / row["image_file_path"]).resolve() if row else None
    if path is None or path.parent != PRODUCTS_DIR or not path.is_file():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(path, headers={"Cache-Control": "public, max-age=86400"})
