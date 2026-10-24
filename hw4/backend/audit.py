"""Audit trail of the shopping assistant's activity (Problem 12).

Every chat request adds one "run" record to `output/audit_trail.json` (path can be changed with
the CAMPUS_CUSTOMS_AUDIT environment variable). A record says when the run happened, which tools
the agent called with brief arguments and results, how many times the model was asked, token use,
and why the run stopped (a final answer, a safety-filter refusal, an error, ...).

Appending only: the file is read, the new run is added to the end of its "runs" list, and the
whole file is written to a temporary file and then swapped in. Earlier runs are never removed or
changed. If the file can't be read as JSON, it is renamed (kept) rather than overwritten.

Privacy: customer messages, names, and emails are NOT recorded: only whether the customer was
signed in, the length of their message, and the page they were on. Tool results are summarized
(product names, prices, stock levels). The assistant's reply is kept as a short preview with the
signed-in customer's name replaced by "[customer]". Anything that looks like an email address is
redacted everywhere.
"""

from __future__ import annotations

import json
import os
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, RetryPromptPart, ToolCallPart, ToolReturnPart, UserPromptPart

AUDIT_PATH = Path(os.environ.get("CAMPUS_CUSTOMS_AUDIT", Path(__file__).resolve().parents[1] / "output" / "audit_trail.json"))
OUTPUT_TOOL = "final_result"  # PydanticAI's built-in tool that carries the structured ChatAnswer
_lock = threading.Lock()
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def new_run_id() -> str:
    return uuid.uuid4().hex[:12]


def _brief(value: Any, limit: int = 200) -> str:
    text = value if isinstance(value, str) else json.dumps(value, default=str, ensure_ascii=False)
    text = _EMAIL.sub("[email redacted]", text)
    return text if len(text) <= limit else text[: limit - 1] + "…"


def redact_reply(reply: str, customer_names: list[str], limit: int = 200) -> str:
    """A short preview of the assistant's reply, with emails and the signed-in customer's name removed."""
    for name in customer_names:
        if name:
            reply = re.sub(rf"\b{re.escape(name)}\b", "[customer]", reply)
    return _brief(reply, limit)


def summarize_result(tool: str, content: Any) -> str:
    """A short, human-readable summary of what a tool returned."""
    if tool == "get_signed_in_customer":
        # The result contains the customer's name and email: keep only whether they were signed in.
        return "guest (not signed in)" if "not signed in" in str(content) else "signed-in customer (name and email redacted)"
    data = content.model_dump() if isinstance(content, BaseModel) else content
    if isinstance(data, dict):
        if "problem" in data:
            return _brief(f"problem: {data['problem']}")
        if "match_quality" in data:
            names = "; ".join(
                f"{m['name']} {m['price_display']} (in stock: {', '.join(m['sizes_in_stock']) or 'none'})" for m in data.get("matches", [])[:3]
            )
            extra = f"; read as: {data['interpreted_as']}" if data.get("interpreted_as") else ""
            return _brief(f"{data['match_quality']}, {data['total_matches']} match(es){': ' + names if names else ''}{extra}", 400)
        if "sizes" in data and "price_display" in data:  # ProductDetails
            return _brief(f"{data['name']}: {data['price_display']}, colors {', '.join(data['colors'])}, {data['total_quantity_available']} in stock", 260)
        if "all_sizes" in data:  # StockCheck
            size = data.get("requested_size")
            if size:
                return _brief(f"{data['name']} size {size}: {data['quantity_available']} available ({data['stock_status']})")
            return _brief(f"{data['name']}: sizes in stock {', '.join(data['sizes_in_stock']) or 'none'}")
    return _brief(data)


def summarize_messages(messages: list[ModelMessage], message: str) -> dict[str, Any]:
    """Tool calls, retries, model steps, and token use for this run only (earlier history is skipped)."""
    # The captured list starts with any earlier conversation; this run begins at the latest request
    # that carries the customer's new message.
    start = 0
    for i, m in enumerate(messages):
        if isinstance(m, ModelRequest) and any(isinstance(p, UserPromptPart) and p.content == message for p in m.parts):
            start = i
    run = messages[start:]

    returns: dict[str, ToolReturnPart] = {}
    retries: dict[str, RetryPromptPart] = {}
    for m in run:
        if isinstance(m, ModelRequest):
            for p in m.parts:
                if isinstance(p, ToolReturnPart):
                    returns[p.tool_call_id] = p
                elif isinstance(p, RetryPromptPart) and p.tool_call_id:
                    retries[p.tool_call_id] = p

    tool_calls, model_steps = [], []
    input_tokens = output_tokens = 0
    for m in run:
        if not isinstance(m, ModelResponse):
            continue
        input_tokens += m.usage.input_tokens or 0
        output_tokens += m.usage.output_tokens or 0
        model_steps.append({"timestamp": m.timestamp.isoformat(timespec="milliseconds"), "model": m.model_name, "finish_reason": m.finish_reason})
        for p in m.parts:
            if not isinstance(p, ToolCallPart):
                continue
            entry: dict[str, Any] = {"called_at": m.timestamp.isoformat(timespec="milliseconds"), "tool": p.tool_name, "arguments": _brief(p.args_as_dict())}
            if p.tool_name == OUTPUT_TOOL:
                args = p.args_as_dict()
                entry["tool"] = f"{OUTPUT_TOOL} (the structured answer)"
                entry["arguments"] = _brief({"reply_chars": len(str(args.get("reply", ""))), "product_ids": args.get("product_ids", []), "display_query": args.get("display_query")})
            if p.tool_call_id in returns:
                r = returns[p.tool_call_id]
                entry["returned_at"] = r.timestamp.isoformat(timespec="milliseconds")
                entry["result"] = "answer accepted" if p.tool_name == OUTPUT_TOOL else summarize_result(p.tool_name, r.content)
                entry["status"] = "ok"
            elif p.tool_call_id in retries:
                r = retries[p.tool_call_id]
                entry["returned_at"] = r.timestamp.isoformat(timespec="milliseconds")
                entry["result"] = _brief(f"rejected, asked to retry: {r.content if isinstance(r.content, str) else r.content}")
                entry["status"] = "retry"
            else:
                entry["status"] = "no result (run stopped)"
            tool_calls.append(entry)
    return {
        "model_requests": len(model_steps),
        "tool_calls": tool_calls,
        "model_steps": model_steps,
        "tokens": {"input": input_tokens, "output": output_tokens},
        "last_finish_reason": model_steps[-1]["finish_reason"] if model_steps else None,
    }


def _load() -> dict[str, Any]:
    if not AUDIT_PATH.exists():
        return {"description": "Campus Customs shopping-assistant audit trail. One record per chat request; new runs are appended.", "runs": []}
    try:
        data = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("runs"), list):
            return data
    except (ValueError, OSError):
        pass
    # Unreadable: keep the old file under a new name instead of overwriting it.
    AUDIT_PATH.rename(AUDIT_PATH.with_name(f"{AUDIT_PATH.stem}.unreadable-{datetime.now():%Y%m%d-%H%M%S}.json"))
    return _load()


def append_run(record: dict[str, Any]) -> None:
    """Add one run to the end of the audit file. Earlier runs are kept exactly as they were."""
    with _lock:
        AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        data = _load()
        data["runs"].append(record)
        data["total_runs"] = len(data["runs"])
        data["last_updated"] = record.get("finished_at")
        tmp = AUDIT_PATH.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, AUDIT_PATH)  # atomic swap: a crash mid-write can't leave a half-written file
