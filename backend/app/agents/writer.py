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


class WriterError(RuntimeError):
    pass


_INLINE_MARKER = re.compile(r"\s*\[\d+(?:\s*,\s*\d+)*\]")


def format_passages(passages: list[Passage]) -> str:
    return "\n\n".join(f"[{p.id}] {p.title} ({p.domain})\n{p.text}" for p in passages)


def structured_writer(llm: Any) -> Runnable:
    return llm.with_structured_output(WriterOutput, include_raw=True)


def usage_from(raw: Any) -> dict[str, int]:
    meta = getattr(raw, "usage_metadata", None) or {}
    return {k: int(meta.get(k, 0)) for k in ("input_tokens", "output_tokens", "total_tokens")}


def enforce_citations(output: WriterOutput, passages: list[Passage]) -> WriterResult:
    valid_ids = {p.id for p in passages}
    claims: list[Claim] = []
    dropped_citations = dropped_claims = 0
    for draft in output.claims:
        cited = list(dict.fromkeys(i for i in draft.citation_ids if i in valid_ids))
        dropped_citations += len(set(draft.citation_ids)) - len(cited)
        text = _INLINE_MARKER.sub("", draft.text).strip()
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
    response = writer.invoke(prompt)
    parsed = response.get("parsed")
    if parsed is None:
        raise WriterError(f"Writer returned unparseable output: {response.get('parsing_error')}")

    result = enforce_citations(parsed, passages)
    result.usage = usage_from(response.get("raw"))
    return result
