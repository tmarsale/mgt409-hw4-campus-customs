"""Tools the shopping assistant can call.

Each tool is a plain function that receives the request's `ChatDeps` through
`RunContext`. To add a tool, write the function here and add it to `TOOLS`;
agent.py registers everything in that list automatically.

The product tools (Problem 6) read the `catalogue` and `inventory` tables through
a read-only database connection. They never touch customer tables, never change
data, and return only shopper-facing fields (no SQL, file paths, or internal IDs
beyond the public product_id).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from pydantic_ai import RunContext

from db import connect
from models import (
    ChatDeps,
    CurrentPage,
    LookupProblem,
    ProductDetails,
    ProductMatch,
    ProductSearchResult,
    SizeAvailability,
    StockCheck,
    stock_status,
)

SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]
MAX_SEARCH_RESULTS = 6

# --- Understanding the customer's words ------------------------------------------------

# Phrases rewritten to one standard word before matching, so different spellings meet.
PHRASES = [
    (r"\b(1\s*/\s*4|1\s*-\s*4|1 4|quarter)[\s-]*zips?\b", " quarterzip "),
    (r"\bfull[\s-]*zip\b", " fullzip "),
    (r"\bt[\s-]*shirts?\b|\btees?\b", " tshirt "),
    (r"\blong[\s-]*sleeves?\b|\bl\s*/\s*s\b", " longsleeve "),
    (r"\bcrew[\s-]*necks?\b", " crewneck "),  # not plain "crew": that's the rowing team (e.g. Crew Left Chest Hoodie)
    (r"\bmock[\s-]*necks?\b", " mockneck "),
    (r"\bhoodies\b|\bhoody\b|\bhooded\b|\bhoods?\b", " hoodie "),
    (r"\bsweatshirts\b|\bsweaters?\b", " sweatshirt "),
    (r"\bjackets\b|\bcoats?\b", " jacket "),
    (r"\bgrey\b", " gray "),
    (r"\bbulldogs\b", " bulldog "),
    (r"\bgame[\s-]*days?\b", " gameday "),
    (r"\bwork(ing)?[\s-]*outs?\b", " workout "),
    (r"\btri[\s-]*blend\b", " triblend "),
    (r"\bold[\s-]*school\b", " oldschool "),
    (r"\bwarm[\s-]*weather\b", " summer "),
    (r"\bwork[\s-]*out\b", " workout "),
]

# Problem 9: vague, descriptive words customers use ("something cozy", "for the gym") that never
# appear in our product names. Each maps to how we read it and the product words that fit it,
# weighted (3 = the best fit, 1 = still fits). Used only when no product is described literally.
INTENT_GROUPS = [
    ({"cozy", "cosy", "comfy", "comfortable", "warm", "warmer", "warmest", "winter", "cold", "chilly", "snug",
      "fall", "autumn", "layer", "layering", "soft", "fuzzy"},
     "warm, cozy layers (fleece, heavyweight sweatshirts, hoodies, quarter-zips)",
     {"fleece": 3, "sherpa": 3, "heavyweight": 3, "hoodie": 2, "quarterzip": 2, "sweatshirt": 1, "crewneck": 1}),
    ({"lightweight", "summer", "hot", "breathable", "spring", "beach"},
     "lightweight T-shirts for warm weather",
     {"triblend": 3, "tshirt": 2}),
    ({"workout", "gym", "running", "run", "athletic", "exercise", "training", "sporty", "active", "jogging", "fitness"},
     "athletic and performance tops",
     {"performance": 3, "dry": 3, "sports": 2, "triblend": 1}),
    ({"dressy", "classy", "smart", "polished", "office", "professional", "interview", "work", "nicer", "elegant", "preppy"},
     "dressier pieces (quarter-zips, mocknecks, jackets)",
     {"brooks": 3, "mockneck": 3, "quarterzip": 2, "bomber": 2, "jacket": 1}),
    ({"gameday", "tailgate", "spirit", "fan", "fans", "cheer", "stadium"},
     "game-day and Yale athletics designs",
     {"football": 3, "bulldog": 2, "sports": 2, "harvard": 2, "athletics": 1}),
    ({"retro", "throwback", "oldschool"},
     "vintage-style designs",
     {"vintage": 3, "felt": 2, "heavyweight": 1}),
    ({"family", "parent", "parents", "relative", "relatives"},
     "family designs (Mom, Dad, Grandpa, and more)",
     {"mom": 3, "dad": 3, "grandpa": 3, "grandma": 3, "aunt": 3, "uncle": 3, "brother": 3, "sister": 3, "cousin": 3}),
]
INTENTS: dict[str, tuple[str, dict[str, int]]] = {w: (label, targets) for ws, label, targets in INTENT_GROUPS for w in ws}
MAX_SUGGESTIONS = 12

# A customer word that should also find these related product words.
RELATED = {
    "sweatshirt": {"sweatshirt", "crewneck", "hoodie", "quarterzip", "fleece"},
    "hoodie": {"hoodie"},
    "pullover": {"pullover", "hoodie", "quarterzip"},
    "jacket": {"jacket", "fleece", "bomber"},
    "fleece": {"fleece", "jacket"},
    "shirt": {"shirt", "tshirt", "longsleeve"},
    "top": {"tshirt", "longsleeve", "crewneck", "hoodie", "quarterzip"},
    "zip": {"quarterzip", "fullzip"},
    "navy": {"navy"},
    "blue": {"blue", "navy"},
}

# Words that name a kind of garment. These must match the product's name or garment type (what it
# actually is), not just its tags or description: e.g. one full-zip fleece is tagged "quarter zip".
GARMENT_WORDS = {
    "hoodie", "tshirt", "quarterzip", "fullzip", "crewneck", "mockneck", "sweatshirt", "longsleeve",
    "jacket", "fleece", "bomber", "pullover",
}

# Words that don't help tell products apart.
STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "for", "in", "on", "with", "do", "you", "have", "has", "is", "are",
    "it", "this", "that", "me", "my", "i", "any", "some", "one", "please", "how", "much", "many", "what",
    "does", "cost", "price", "available", "stock", "size", "sizes", "about", "tell", "more", "show", "find",
    "looking", "want", "need", "your", "store", "campus", "customs", "item", "items", "product", "products",
    "merch", "merchandise", "apparel", "gear",
    # Problem 9: filler common in vague requests ("something nice to wear", "can you recommend…").
    "something", "anything", "nice", "good", "great", "cool", "recommend", "recommendation", "recommendations",
    "suggest", "suggestion", "suggestions", "like", "would", "could", "should", "can", "wear", "wearing", "buy",
    "get", "gift", "gifts", "present", "really", "very", "kind", "type", "outfit", "clothes", "clothing", "to",
    "be", "im", "am", "we", "our", "us", "will", "go", "going", "idea", "ideas", "options", "option", "stuff",
    "weather", "season", "seasons", "days", "nights", "time", "times", "occasion", "occasions", "around",
}
# Words on almost every product: they count a little, but never decide a match on their own.
COMMON = {"yale", "university"}

SIZE_WORDS = {
    "xs": "XS", "extra small": "XS", "x-small": "XS", "xsmall": "XS",
    "s": "S", "small": "S", "sm": "S",
    "m": "M", "medium": "M", "med": "M", "md": "M",
    "l": "L", "large": "L", "lg": "L",
    "xl": "XL", "extra large": "XL", "x-large": "XL", "xlarge": "XL",
    "xxl": "XXL", "2xl": "XXL", "2x": "XXL", "xx-large": "XXL", "xxlarge": "XXL", "double xl": "XXL",
    "extra extra large": "XXL",
}


def normalize(text: str) -> str:
    text = text.lower()
    for pattern, replacement in PHRASES:
        text = re.sub(pattern, replacement, text)
    return text


def words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", normalize(text)) if w not in STOPWORDS}


def standard_size(size: str) -> str | None:
    return SIZE_WORDS.get(re.sub(r"\s+", " ", size.strip().lower()))


def _price_display(price: float) -> str:
    return f"${price:,.2f}"


def _sizes(conn, product_id: str) -> list[SizeAvailability]:
    rows = conn.execute("SELECT size, quantity FROM inventory WHERE product_id = ?", (product_id,)).fetchall()
    rank = {s: i for i, s in enumerate(SIZE_ORDER)}
    rows = sorted(rows, key=lambda r: rank.get(r["size"], len(SIZE_ORDER)))
    return [SizeAvailability(size=r["size"], quantity_available=r["quantity"], stock_status=stock_status(r["quantity"])) for r in rows]


def _short(description: str, limit: int = 160) -> str:
    return description if len(description) <= limit else description[: limit - 1].rsplit(" ", 1)[0] + "…"


# --- Tools ----------------------------------------------------------------------------


def get_signed_in_customer(ctx: RunContext[ChatDeps]) -> str:
    """Find out whether the customer chatting is signed in, and if so their name and the email on their account.

    Use the name to personalize replies. Mention the email only if the customer asks about their own account.
    Never returns a password, password hash, or anything about other customers.
    """
    d = ctx.deps
    if not d.customer_first_name:
        return "The customer is not signed in (a guest). Their chat isn't saved."
    full_name = " ".join(n for n in (d.customer_first_name, d.customer_last_name) if n)
    return f"The customer is signed in as {full_name} (email on the account: {d.customer_email}). Their chat history is saved to their account."


# --- Current page (Problem 8) -------------------------------------------------------------

STATIC_PAGES = {
    "/": ("home", "the Home page"),
    "/about": ("about", "the About Us page"),
    "/login": ("login", "the Log In page"),
    "/create-account": ("create-account", "the Create Account page"),
}


def describe_page(path: str | None) -> CurrentPage | None:
    """Work out which page the customer is on from its path. Product pages are checked against the catalogue."""
    if not path:
        return None
    path = path.split("?")[0].split("#")[0].rstrip("/") or "/"
    if path in STATIC_PAGES:
        kind, description = STATIC_PAGES[path]
        return CurrentPage(kind=kind, description=description)
    if path == "/products":
        return CurrentPage(kind="shop", description="the Shop All page (the product list)")
    match = re.fullmatch(r"/products/([a-z0-9-]{1,120})", path)
    if match:
        with connect() as conn:
            row = conn.execute("SELECT product_id, name FROM catalogue WHERE product_id = ?", (match.group(1),)).fetchone()
        if row:
            return CurrentPage(kind="product", description=f"the product page for {row['name']}", product_id=row["product_id"], product_name=row["name"])
    return CurrentPage(kind="other", description="a page of the Campus Customs website")


@dataclass
class SearchOutcome:
    """The result of one catalogue search, shared by the assistant's tool and GET /api/search."""

    quality: str  # "exact name" | "strong" | "suggestions" | "partial" | "none"
    product_ids: list[str]  # every match, best first
    interpreted_as: str | None = None  # for "suggestions": how a vague request was read


def find_products(query: str) -> SearchOutcome:
    """Rank catalogue products for a customer's words. Read-only; used by the chat and by the Products page."""
    wanted = words(query)
    # Vague words ("cozy", "gym") that aren't in any product name are read as an intent, not matched literally.
    vague = {w for w in wanted if w in INTENTS}
    distinctive = wanted - COMMON - vague
    with connect() as conn:
        rows = conn.execute("SELECT * FROM catalogue").fetchall()
        stock = dict(conn.execute("SELECT product_id, SUM(quantity) FROM inventory GROUP BY product_id").fetchall())

    def product_words(row):
        name_words = words(row["name"])
        type_words = name_words | words(row["garment_type"])
        all_words = type_words | words(row["description"]) | words(" ".join(json.loads(row["colors"]) + json.loads(row["search_tags"])))
        return name_words, type_words, all_words

    def matches_word(word, name_words, type_words, all_words):
        options = RELATED.get(word, {word})
        if options & name_words:
            return 3
        return 1 if options & (type_words if word in GARMENT_WORDS else all_words) else 0

    if vague:
        return _suggest(query, vague, distinctive, rows, stock, product_words, matches_word)

    scored = []
    for row in rows:
        name_words, type_words, all_words = product_words(row)
        matched, score = 0, 0.0
        for word in distinctive:
            points = matches_word(word, name_words, type_words, all_words)
            if points:
                matched, score = matched + 1, score + points
            if word in all_words:  # the customer's exact word beats a related one ("pullover" hoodie > full-zip hoodie)
                score += 0.5
        score += 0.5 * len((wanted & COMMON) & all_words)
        exact = normalize(row["name"]).split() == normalize(query).split()
        if exact:
            score += 100
        if matched or exact or (not distinctive and wanted & all_words):
            scored.append((exact, matched, score, row["product_id"]))
    if not scored:
        return SearchOutcome("none", [])
    scored.sort(key=lambda s: (s[0], s[1], s[2]), reverse=True)
    best_exact, best_matched = scored[0][0], scored[0][1]
    if best_exact:
        return SearchOutcome("exact name", [scored[0][3]])
    if distinctive and best_matched == len(distinctive):
        return SearchOutcome("strong", [s[3] for s in scored if s[1] == len(distinctive)])
    return SearchOutcome("partial", [s[3] for s in scored])


def _suggest(query, vague, distinctive, rows, stock, product_words, matches_word) -> SearchOutcome:
    """Problem 9: turn a vague request into a short, ranked list of products that really fit it.

    Any concrete words the customer also used (a color, "hoodie", a college) must all match.
    In-stock products come first, then the best fit, then the most stock.
    """
    labels = list(dict.fromkeys(INTENTS[w][0] for w in sorted(vague)))
    targets: dict[str, int] = {}
    for w in vague:
        for target, weight in INTENTS[w][1].items():
            targets[target] = max(weight, targets.get(target, 0))
    ranked = []
    for row in rows:
        name_words, type_words, all_words = product_words(row)
        if any(not matches_word(w, name_words, type_words, all_words) for w in distinctive):
            continue
        fit = sum(weight * (2 if target in type_words else 1)
                  for target, weight in targets.items()
                  if target in (type_words if target in GARMENT_WORDS else all_words))
        if fit:
            qty = stock.get(row["product_id"]) or 0
            ranked.append((qty > 0, fit, qty, row["product_id"]))
    if not ranked:
        return SearchOutcome("none", [], interpreted_as="; ".join(labels))
    ranked.sort(reverse=True)
    return SearchOutcome("suggestions", [r[3] for r in ranked[:MAX_SUGGESTIONS]], interpreted_as="; ".join(labels))


def search_products(ctx: RunContext[ChatDeps], query: str) -> ProductSearchResult:
    """Search the Campus Customs catalogue by product name, type, color, sport, college, or keywords.

    Use this first whenever a customer mentions a product or kind of product, before giving any
    price, description, or availability. Pass the product words only (e.g. "basic hoodie big yale",
    "navy crewneck", "Saybrook quarter zip"), not the size. For vague requests ("something cozy",
    "a shirt for the gym", "something dressy in navy") pass the customer's own descriptive words:
    the search understands them and returns `match_quality` "suggestions". Returns the best matches
    with their real prices and which sizes are in stock, plus `match_quality` telling you how sure the match is.
    """
    query = query.strip()[:120]
    outcome = find_products(query)
    ctx.deps.searches[query] = (outcome.quality, outcome.product_ids)  # the full ranked list, for the web page
    shown = outcome.product_ids[:MAX_SEARCH_RESULTS]
    matches = []
    with connect() as conn:
        rows = {r["product_id"]: r for r in conn.execute(
            f"SELECT * FROM catalogue WHERE product_id IN ({','.join('?' * len(shown))})", shown)}
        for pid in shown:
            row = rows[pid]
            sizes = _sizes(conn, pid)
            matches.append(
                ProductMatch(
                    product_id=pid,
                    name=row["name"],
                    garment_type=row["garment_type"],
                    price=row["price"],
                    price_display=_price_display(row["price"]),
                    total_quantity_available=sum(s.quantity_available for s in sizes),
                    sizes_in_stock=[s.size for s in sizes if s.quantity_available > 0],
                    short_description=_short(row["description"]),
                )
            )
    ctx.deps.seen_product_ids.update(shown)

    quality, total = outcome.quality, len(outcome.product_ids)
    if quality == "none":
        note = ("Nothing in the catalogue matches. Tell the customer you couldn't find it and ask them to "
                "describe it differently. Don't suggest an unrelated product as if it were what they asked for.")
    elif quality == "exact name":
        note = "This is the product the customer named."
    elif quality == "suggestions":
        note = (f"The customer's request was vague, so these are suggestions that fit it, read as: {outcome.interpreted_as}. "
                "In-stock products are listed first. Say briefly how you understood the request, recommend 2-4 of these "
                "by name with their real prices and a short reason each fits, then ask one question to narrow it down "
                f"(e.g. color, budget, or style). To show all {total} suggestions on the web page, set display_query to {query!r}.")
    elif quality == "strong" and total == 1:
        note = f"One product matches all the customer's words. To show it on the web page, set display_query to {query!r}."
    elif quality == "strong":
        note = (f"{total} products match. If the customer means one specific item, list a few names "
                "and ask which one they mean before quoting a single price or stock level. To show all "
                f"{total} on the web page, set display_query to {query!r}.")
    else:
        note = ("These only partly match the customer's words, so no product matches what they asked for. "
                "Don't assume any of them is what they want and don't show them on the page: say no matching "
                "products were found and ask a clarifying question.")
    return ProductSearchResult(query=query, match_quality=quality, total_matches=total, matches=matches,
                               interpreted_as=outcome.interpreted_as, note=note)


def get_product_details(ctx: RunContext[ChatDeps], product_id: str) -> ProductDetails | LookupProblem:
    """Get the full description, colors, real price, and stock for every size of one product.

    Use it when the customer asks to know more about a specific product, or before
    answering detailed questions about it. `product_id` must come from `search_products`.
    """
    with connect() as conn:
        row = conn.execute("SELECT * FROM catalogue WHERE product_id = ?", (product_id.strip(),)).fetchone()
        if row is None:
            return LookupProblem(problem=f"No product has the id '{product_id}'.", suggestion="Use search_products to find the right product_id.")
        sizes = _sizes(conn, row["product_id"])
    ctx.deps.seen_product_ids.add(row["product_id"])
    ctx.deps.looked_up_ids.append(row["product_id"])
    return ProductDetails(
        product_id=row["product_id"],
        name=row["name"],
        garment_type=row["garment_type"],
        description=row["description"],
        colors=json.loads(row["colors"]),
        price=row["price"],
        price_display=_price_display(row["price"]),
        sizes=sizes,
        total_quantity_available=sum(s.quantity_available for s in sizes),
        product_page=f"/products/{row['product_id']}",
    )


def check_stock(ctx: RunContext[ChatDeps], product_id: str, size: str | None = None) -> StockCheck | LookupProblem:
    """Check live stock for one product, either one size (e.g. "medium", "L", "XXL") or all sizes.

    Use it for "do you have it in medium?" or "how many are left in large?".
    `product_id` must come from `search_products`. Leave `size` empty to see every size.
    """
    requested = None
    if size and size.strip():
        requested = standard_size(size)
        if requested is None:
            return LookupProblem(
                problem=f"'{size}' isn't one of the store's sizes.",
                suggestion="Sizes are XS, S, M, L, XL, and XXL. Ask the customer which of these they mean.",
            )
    with connect() as conn:
        row = conn.execute("SELECT product_id, name, price FROM catalogue WHERE product_id = ?", (product_id.strip(),)).fetchone()
        if row is None:
            return LookupProblem(problem=f"No product has the id '{product_id}'.", suggestion="Use search_products to find the right product_id.")
        sizes = _sizes(conn, row["product_id"])
    ctx.deps.seen_product_ids.add(row["product_id"])
    ctx.deps.looked_up_ids.append(row["product_id"])
    chosen = next((s for s in sizes if s.size == requested), None)
    return StockCheck(
        product_id=row["product_id"],
        name=row["name"],
        price_display=_price_display(row["price"]),
        requested_size=requested,
        quantity_available=chosen.quantity_available if chosen else None,
        stock_status=chosen.stock_status if chosen else None,
        sizes_in_stock=[s.size for s in sizes if s.quantity_available > 0],
        all_sizes=sizes,
    )


TOOLS = [get_signed_in_customer, search_products, get_product_details, check_stock]
