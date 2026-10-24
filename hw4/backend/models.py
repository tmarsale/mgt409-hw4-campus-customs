"""Pydantic models for the shopping-assistant chat."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field

MAX_MESSAGE_CHARS = 1000
MAX_HISTORY_TURNS = 20


class ChatTurn(BaseModel):
    """One earlier message in the conversation, as shown in the chat window."""

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)
    product_ids: list[str] = Field(
        default_factory=list, max_length=3,
        description="Assistant turns only: the product(s) that reply was about, as returned by the server "
        "(context_product_ids). Lets follow-ups like 'Does it come in blue?' work for guests. Checked against the catalogue.",
    )


class PageContext(BaseModel):
    """Which page the customer is looking at while chatting (Problem 8)."""

    path: str = Field(max_length=200, description="The website path, e.g. '/products/basic-hoodie-big-yale'.")


class ChatRequest(BaseModel):
    """What the website sends: the new message, recent conversation (used for guests), and the current page."""

    message: str = Field(min_length=1, max_length=MAX_MESSAGE_CHARS)
    history: list[ChatTurn] = Field(default_factory=list, max_length=MAX_HISTORY_TURNS)
    page: PageContext | None = None


class ProductCard(BaseModel):
    """A product the assistant is talking about, shown as a card under its reply.

    Cards are built by the backend from the database, only for product_ids that a tool
    actually returned during the conversation turn, never from text the AI wrote.
    """

    product_id: str
    name: str
    price: float
    image_url: str
    url: str


class DisplayProduct(BaseModel):
    """One product card shown on the web page. Every field is read from the database.

    The fields match the website's existing product cards (the same shape as GET /api/products),
    so the frontend reuses its ProductCard component and image handling unchanged.
    """

    product_id: str = Field(description="catalogue.product_id; the card links to /products/{product_id}.")
    name: str = Field(description="catalogue.name")
    garment_type: str = Field(description="catalogue.garment_type, used for the card's category label.")
    price: float = Field(description="catalogue.price")
    image_url: str = Field(description="Public URL of the photo, built from catalogue.image_file_path.")
    short_description: str = Field(description="First ~160 characters of catalogue.description.")
    description: str = Field(description="Full catalogue.description (the card shows the first two lines).")
    colors: list[str]
    search_tags: list[str]
    total_stock: int = Field(description="Sum of inventory.quantity across sizes.")
    sizes_in_stock: list[str]
    url: str = Field(description="The single-product page from Problem 3.")


class PageResults(BaseModel):
    """Products the assistant found, to show as cards on the web page."""

    query: str = Field(description="The search the products came from.")
    total: int
    products: list[DisplayProduct]


class ChatResponse(BaseModel):
    """What the backend sends back to the chat window."""

    reply: str
    products: list[ProductCard] = Field(default_factory=list)
    page_results: PageResults | None = Field(
        default=None,
        description="Products to show on the page. total=0 means the customer searched but nothing matched. "
        "Null when the reply isn't a product search.",
    )
    saved: bool = Field(default=False, description="True when this exchange was saved to the customer's account.")
    context_product_ids: list[str] = Field(
        default_factory=list,
        description="Problem 9: the product(s) this conversation is now about, so a follow-up like 'Does it come in blue?' "
        "knows what 'it' is. Guests send these back on the assistant turn in `history`.",
    )


class HistoryMessage(BaseModel):
    """One saved message, as reloaded into the chat window."""

    role: Literal["user", "assistant"]
    content: str
    products: list[ProductCard] = Field(default_factory=list)
    page_results: PageResults | None = None
    created_at: str


class ChatHistory(BaseModel):
    """GET /api/chat/history: the signed-in customer's saved conversation (empty for guests)."""

    signed_in: bool
    messages: list[HistoryMessage]


@dataclass
class CurrentPage:
    """The page the customer is on, worked out and checked by the backend (never taken on trust)."""

    kind: Literal["home", "shop", "product", "about", "login", "create-account", "other"]
    description: str
    product_id: str | None = None
    product_name: str | None = None


@dataclass
class ChatDeps:
    """Per-request information the agent's tools may use. Built by the backend, never by the AI."""

    customer_first_name: str | None = None
    customer_last_name: str | None = None
    customer_email: str | None = None
    current_page: CurrentPage | None = None
    # Every product_id a tool returned during this request. Product cards may only show these,
    # so the AI can never put an invented product on screen.
    seen_product_ids: set[str] = field(default_factory=set)
    # Every search the agent ran this turn: query -> (match_quality, ALL matching ids, best first).
    # Products shown on the page come only from here.
    searches: dict[str, tuple[str, list[str]]] = field(default_factory=dict)
    # Problem 9: the product(s) the previous reply was about, as (product_id, name), checked against the
    # catalogue. Lets the agent answer "Does it come in blue?" without asking which product.
    recent_products: list[tuple[str, str]] = field(default_factory=list)
    # Products looked up one at a time (details or stock) this turn, in order.
    looked_up_ids: list[str] = field(default_factory=list)


# --- Problem 6: product lookups (read from the `catalogue` and `inventory` tables) ---------

StockStatus = Literal["in stock", "low stock", "out of stock"]
LOW_STOCK_THRESHOLD = 3  # same rule as the website: 1-3 left counts as low stock


def stock_status(quantity: int) -> StockStatus:
    if quantity <= 0:
        return "out of stock"
    return "low stock" if quantity <= LOW_STOCK_THRESHOLD else "in stock"


class SizeAvailability(BaseModel):
    """One row of `inventory`: how many of one size are available."""

    size: str = Field(description="XS, S, M, L, XL, or XXL (inventory.size).")
    quantity_available: int = Field(description="Units in stock right now (inventory.quantity).")
    stock_status: StockStatus


class ProductMatch(BaseModel):
    """A short summary of one product, as returned by a search."""

    product_id: str = Field(description="catalogue.product_id. Use it for detail and stock lookups.")
    name: str
    garment_type: str
    price: float = Field(description="catalogue.price in US dollars.")
    price_display: str = Field(description="The price formatted for customers, e.g. '$68.00'. Quote this exactly.")
    total_quantity_available: int = Field(description="All sizes added together.")
    sizes_in_stock: list[str] = Field(description="Sizes with at least one unit available, in size order.")
    short_description: str


class ProductSearchResult(BaseModel):
    """What `search_products` returns."""

    query: str
    match_quality: Literal["exact name", "strong", "suggestions", "partial", "none"] = Field(
        description="'exact name' = the query is a product's name; 'strong' = all search words matched; "
        "'suggestions' = a vague request (e.g. 'something cozy') matched to products that fit it; "
        "'partial' = only some words matched (ask the customer before assuming); 'none' = nothing found."
    )
    interpreted_as: str | None = Field(
        default=None, description="For 'suggestions': how the vague request was understood, to explain to the customer."
    )
    total_matches: int = Field(description="How many products matched in total (only the best few are listed).")
    matches: list[ProductMatch]
    note: str = Field(description="Plain-language guidance for answering this result.")


class ProductDetails(BaseModel):
    """Everything the store knows about one product: catalogue fields plus stock for every size."""

    product_id: str
    name: str
    garment_type: str
    description: str = Field(description="catalogue.description, the full product description.")
    colors: list[str]
    price: float
    price_display: str
    sizes: list[SizeAvailability]
    total_quantity_available: int
    product_page: str = Field(description="Where the customer can see this product on the website.")


class StockCheck(BaseModel):
    """Availability of one product in one requested size (or all sizes)."""

    product_id: str
    name: str
    price_display: str
    requested_size: str | None = Field(description="The size asked about, standardized (e.g. 'medium' -> 'M'); null = all sizes.")
    quantity_available: int | None = Field(description="Units of the requested size in stock; null when no single size was asked.")
    stock_status: StockStatus | None
    sizes_in_stock: list[str] = Field(description="All sizes currently available, to suggest alternatives.")
    all_sizes: list[SizeAvailability]


class LookupProblem(BaseModel):
    """Returned instead of a result when a lookup can't be answered, e.g. an unknown product_id or size."""

    problem: str
    suggestion: str


class ChatAnswer(BaseModel):
    """The agent's structured answer: its message plus the products it is talking about."""

    reply: str = Field(description="The message to show the customer.")
    product_ids: list[str] = Field(
        default_factory=list,
        description="Up to 3 product_ids that this reply is specifically about (shown as product cards). "
        "Only ids returned by a tool in this conversation turn. Leave empty for general answers, clarifying questions, or 'not found'.",
    )
    display_query: str | None = Field(
        default=None,
        description="To show a search's matching products on the web page, the exact `query` you passed to search_products "
        "this turn. Only for 'exact name', 'strong', or 'suggestions' results. Null when not showing products on the page.",
    )
