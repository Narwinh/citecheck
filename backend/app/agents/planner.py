"""Planner agent: question -> 1..N web search sub-queries."""

from dataclasses import dataclass, field
from typing import Any

from langchain_core.runnables import Runnable
from pydantic import BaseModel, Field

from app.agents.llm import invoke_structured, structured
from app.prompts import render

PROMPT = "planner_v1"


class PlannerOutput(BaseModel):
    sub_queries: list[str] = Field(description="Short keyword-style web search queries.")


@dataclass
class PlanResult:
    sub_queries: list[str]
    usage: dict[str, int] = field(default_factory=dict)


def structured_planner(llm: Any) -> Runnable:
    return structured(llm, PlannerOutput)


def clean_queries(queries: list[str], question: str, max_queries: int) -> list[str]:
    """Strip, drop blanks and duplicates, cap the count; fall back to the question."""
    seen: set[str] = set()
    cleaned: list[str] = []
    for q in queries:
        q = " ".join(q.split())
        if q and q.lower() not in seen:
            seen.add(q.lower())
            cleaned.append(q)
    return cleaned[:max_queries] or [question]


def plan(question: str, planner: Runnable, max_queries: int = 4) -> PlanResult:
    prompt = render(PROMPT, question=question, max_queries=str(max_queries))
    parsed, usage = invoke_structured(planner, prompt, "Planner")
    return PlanResult(clean_queries(parsed.sub_queries, question, max_queries), usage)
