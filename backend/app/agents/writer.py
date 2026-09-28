"""Writer agent: question + passages -> claims, each citing at least one passage.

The LLM returns structured output (WriterOutput). We then enforce the
citation contract in code rather than trusting the model: citation IDs that
do not match a passage are dropped, and a claim left with no valid citation
is dropped too. Both are counted so the eval can report how often it happens.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Literal

from langchain_core.runnables import Runnable
from pydantic import BaseModel, Field

from app.agents.llm import format_passages, invoke_structured, structured
from app.prompts import render
from app.state import Claim, Passage

PROMPT = "writer_v1"


class DraftClaim(BaseModel):
    text: str = Field(description="One self-contained declarative sentence, no [n] markers.")
    citation_ids: list[int] = Field(description="IDs of the passages that state this claim.")


class WriterOutput(BaseModel):
    status: Literal["answered", "partial", "unanswerable"]
    claims: list[DraftClaim] = Field(description="Empty when status is unanswerable.")
    missing: str | None = Field(description="What the passages do not cover, or null.")


@dataclass
class WriterResult:
    status: Literal["answered", "partial", "unanswerable"]
    claims: list[Claim]
    missing: str | None
    usage: dict[str, int] = field(default_factory=dict)
    dropped_citations: int = 0  # citation IDs that pointed at no passage
    dropped_claims: int = 0  # claims left with zero valid citations


_INLINE_MARKER = re.compile(r"\s*\[\d+(?:\s*,\s*\d+)*\]")


def clean_text(text: str) -> str:
    return _INLINE_MARKER.sub("", text).strip()


def valid_citations(ids: list[int], passages: list[Passage]) -> list[int]:
    """Keep IDs that name a real passage, deduplicated, in the model's order."""
    valid_ids = {p.id for p in passages}
    return list(dict.fromkeys(i for i in ids if i in valid_ids))


def structured_writer(llm: Any) -> Runnable:
    return structured(llm, WriterOutput)


def enforce_citations(output: WriterOutput, passages: list[Passage]) -> WriterResult:
    claims: list[Claim] = []
    dropped_citations = dropped_claims = 0
    for draft in output.claims:
        cited = valid_citations(draft.citation_ids, passages)
        dropped_citations += len(set(draft.citation_ids)) - len(cited)
        text = clean_text(draft.text)
        if not cited or not text:
            dropped_claims += 1
            continue
        claims.append(Claim(id=len(claims) + 1, text=text, citation_ids=cited))

    status = output.status
    if status != "unanswerable" and not claims:
        status = "unanswerable"  # nothing survived, so nothing can be claimed
    return WriterResult(status, claims, output.missing, {}, dropped_citations, dropped_claims)


def write(question: str, passages: list[Passage], writer: Runnable) -> WriterResult:
    if not passages:
        return WriterResult("unanswerable", [], "No sources were found for this question.")

    prompt = render(PROMPT, question=question, passages=format_passages(passages))
    parsed, usage = invoke_structured(writer, prompt, "Writer")
    result = enforce_citations(parsed, passages)
    result.usage = usage
    return result
