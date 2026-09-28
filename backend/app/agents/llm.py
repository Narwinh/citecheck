"""Helpers shared by the LLM-backed agents."""

from typing import Any

from langchain_core.runnables import Runnable
from pydantic import BaseModel

from app.state import Passage

USAGE_KEYS = ("input_tokens", "output_tokens", "total_tokens")


class AgentOutputError(RuntimeError):
    pass


def structured(llm: Any, schema: type[BaseModel]) -> Runnable:
    """Structured output with the raw message kept (for token usage).

    `llm` may be one chat model or a list [primary, fallback, ...]; with a list,
    each later model is tried only if the earlier one raises.
    """
    models = llm if isinstance(llm, list) else [llm]
    chains = [m.with_structured_output(schema, include_raw=True) for m in models]
    return chains[0].with_fallbacks(chains[1:]) if len(chains) > 1 else chains[0]


def usage_from(raw: Any) -> dict[str, int]:
    """Token counts plus a per-model call counter, e.g. {"calls:gemini-3.7-flash": 1}."""
    meta = getattr(raw, "usage_metadata", None) or {}
    usage = {k: int(meta.get(k, 0)) for k in USAGE_KEYS}
    model = (getattr(raw, "response_metadata", None) or {}).get("model_name")
    if model:
        usage[f"calls:{model}"] = 1
    return usage


def add_usage(total: dict[str, int], more: dict[str, int]) -> dict[str, int]:
    return {k: total.get(k, 0) + more.get(k, 0) for k in total.keys() | more.keys()}


def invoke_structured(runnable: Runnable, prompt: str, agent: str) -> tuple[Any, dict[str, int]]:
    """Invoke a structured-output runnable; return (parsed, usage) or raise."""
    response = runnable.invoke(prompt)
    parsed = response.get("parsed")
    if parsed is None:
        raise AgentOutputError(
            f"{agent} returned unparseable output: {response.get('parsing_error')}"
        )
    return parsed, usage_from(response.get("raw"))


def format_passages(passages: list[Passage]) -> str:
    return "\n\n".join(f"[{p.id}] {p.title} ({p.domain})\n{p.text}" for p in passages)
