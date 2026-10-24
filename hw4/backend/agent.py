"""The Campus Customs shopping assistant, built with PydanticAI.

- System prompt: loaded from prompts/prompt.md next to this file.
- AI model: OPENAI_MODEL (default gpt-5.6-luna), called through Portkey with the
  PORTKEY_API_KEY from the environment or a .env file. The key is never hard-coded,
  logged, or returned to the website.
- Tools: everything listed in tools.TOOLS (customer first name, product search,
  product details, and stock checks).
- Output: a `ChatAnswer` (reply text + product_ids for cards). A validator rejects any
  product_id that a tool didn't return in this turn, so cards can't show invented products.

The agent is created on first use, so the rest of the website still works if the
API key is missing; only the chat reports that the assistant is unavailable.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")  # keep the server log free of the library's startup banner

from dotenv import load_dotenv  # noqa: E402
from openai import AsyncOpenAI  # noqa: E402
from pydantic_ai import Agent, ModelRetry, RunContext  # noqa: E402
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, UserPromptPart  # noqa: E402
from pydantic_ai.models.openai import OpenAIChatModel  # noqa: E402
from pydantic_ai.providers.openai import OpenAIProvider  # noqa: E402
from pydantic_ai.usage import UsageLimits  # noqa: E402

from models import ChatAnswer, ChatDeps, ChatTurn  # noqa: E402
from tools import TOOLS  # noqa: E402

load_dotenv()  # picks up a .env file if there is one; existing environment variables win

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "prompt.md"
PORTKEY_BASE_URL = "https://api.portkey.ai/v1"
DEFAULT_MODEL = "gpt-5.6-luna"
REQUEST_TIMEOUT_SECONDS = 45
# Hard stop for one customer message (Problem 12). Normal answers use 2-4 model calls and 1-3 tools;
# these caps only stop a runaway loop, which ends the run with UsageLimitExceeded.
USAGE_LIMITS = UsageLimits(request_limit=10, tool_calls_limit=15)


class AssistantNotConfigured(RuntimeError):
    """Raised when PORTKEY_API_KEY is missing."""


def model_name() -> str:
    return os.environ.get("OPENAI_MODEL", DEFAULT_MODEL)


def load_system_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


MAX_PRODUCT_CARDS = 3


def only_looked_up_products(ctx: RunContext[ChatDeps], answer: ChatAnswer) -> ChatAnswer:
    """Product cards may only show products a tool actually returned in this turn."""
    unknown = [pid for pid in answer.product_ids if pid not in ctx.deps.seen_product_ids]
    if unknown:
        raise ModelRetry(
            f"product_ids {unknown} were not returned by a tool in this turn. Look them up with search_products "
            "first, or leave product_ids empty."
        )
    answer.product_ids = list(dict.fromkeys(answer.product_ids))[:MAX_PRODUCT_CARDS]

    # Products shown on the page must come from a real, good match the agent searched for this turn.
    if answer.display_query is not None:
        searched = ctx.deps.searches.get(answer.display_query)
        if searched is None:
            raise ModelRetry(
                f"display_query {answer.display_query!r} is not a search you ran this turn. Use the exact query string "
                f"you passed to search_products ({list(ctx.deps.searches)}), or set display_query to null."
            )
        quality, ids = searched
        if quality not in ("exact name", "strong", "suggestions") or not ids:
            raise ModelRetry(
                f"The search {answer.display_query!r} had match_quality {quality!r}, so its results don't match what the "
                "customer asked for. Set display_query to null and tell the customer no matching products were found."
            )
    return answer


@lru_cache(maxsize=1)
def get_agent() -> Agent[ChatDeps, ChatAnswer]:
    api_key = os.environ.get("PORTKEY_API_KEY")
    if not api_key:
        raise AssistantNotConfigured("PORTKEY_API_KEY is not set")
    client = AsyncOpenAI(
        api_key=api_key,
        base_url=PORTKEY_BASE_URL,
        default_headers={"x-portkey-api-key": api_key, "x-portkey-provider": "openai"},
        timeout=REQUEST_TIMEOUT_SECONDS,
        max_retries=2,
    )
    agent = Agent(
        OpenAIChatModel(model_name(), provider=OpenAIProvider(openai_client=client)),
        deps_type=ChatDeps,
        output_type=ChatAnswer,
        # `instructions` (not `system_prompt`) on purpose: PydanticAI adds a system_prompt only when a
        # conversation starts, so it would be missing whenever the website sends earlier messages as
        # history. Instructions are sent with every request.
        instructions=load_system_prompt(),
        tools=TOOLS,
        name="campus-customs-assistant",
        retries=2,
    )
    agent.output_validator(only_looked_up_products)
    agent.instructions(conversation_context)
    return agent


def conversation_context(ctx: RunContext[ChatDeps]) -> str:
    """Extra instructions added to every request: who is chatting, which page they're on (Problem 8), and the
    product the conversation was just about, so follow-ups like "Does it come in blue?" work (Problem 9)."""
    d = ctx.deps
    lines = ["# This conversation"]
    if d.customer_first_name:
        name = " ".join(n for n in (d.customer_first_name, d.customer_last_name) if n)
        lines.append(
            f"- The customer is **signed in as {name}**. Use their first name naturally (not in every message). "
            "Their email is available from get_signed_in_customer if they ask about their own account. "
            "Earlier messages in this conversation come from their saved chat history."
        )
    else:
        lines.append("- The customer is a **guest** (not signed in). Their chat isn't saved; signing in would save it.")
    recent = d.recent_products
    if len(recent) == 1:
        pid, name = recent[0]
        lines.append(
            f"- The **most recently discussed product** is **{name}** (product_id `{pid}`). If the customer asks a follow-up "
            "without naming a product (\"Does it come in blue?\", \"Is it in stock in large?\", \"How much is that one?\"), "
            "they mean this product: look it up with get_product_details or check_stock using that product_id, and don't "
            "ask them to repeat the name. Include it in product_ids when your reply is about it."
        )
    elif recent:
        listed = "; ".join(f"{name} (product_id `{pid}`)" for pid, name in recent)
        lines.append(
            f"- The previous reply was about several products: {listed}. If a follow-up like \"does it come in blue?\" "
            "clearly fits only one of them, use that one; otherwise ask which one they mean, naming them."
        )
    page = d.current_page
    if page is None:
        lines.append("- The page they're on is unknown.")
    elif page.kind == "product":
        if recent and all(pid != page.product_id for pid, _ in recent):
            # Two candidates for "it": the product on screen and the one just discussed in the chat.
            lines.append(
                f"- They are **viewing {page.description}** (product_id `{page.product_id}`), a different product from the "
                "one just discussed. \"This\", \"this one\", or \"the one I'm looking at\" means the page's product; \"it\" or "
                "\"that one\" in a direct follow-up to your last reply means the product just discussed. If you can't tell, ask briefly."
            )
        else:
            lines.append(
                f"- They are **viewing {page.description}** (product_id `{page.product_id}`). When they say \"this\", \"it\", "
                "\"this one\", or ask about a color, size, price, or stock without naming a product, they mean this product: "
                "look it up with get_product_details or check_stock using that product_id. If they clearly name a different "
                "product, use that one instead."
            )
    else:
        lines.append(f"- They are on {page.description}. No specific product is open, so ask which product they mean if it's unclear.")
    return "\n".join(lines)


def to_message_history(turns: list[ChatTurn]) -> list[ModelMessage]:
    """Turn the chat window's earlier messages into PydanticAI's message format."""
    history: list[ModelMessage] = []
    for turn in turns:
        if turn.role == "user":
            history.append(ModelRequest(parts=[UserPromptPart(content=turn.content)]))
        else:
            history.append(ModelResponse(parts=[TextPart(content=turn.content)]))
    return history


async def ask_assistant(message: str, turns: list[ChatTurn], deps: ChatDeps) -> ChatAnswer:
    """Send one customer message (plus recent conversation) to the agent and return its answer."""
    result = await get_agent().run(message, message_history=to_message_history(turns), deps=deps, usage_limits=USAGE_LIMITS)
    answer = result.output
    answer.reply = answer.reply.strip()
    return answer
