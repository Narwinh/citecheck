"""Shared data models passed between agents."""

from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel


class Passage(BaseModel):
    id: int  # 1-based, stable within one request; what the writer cites as [id]
    url: str
    title: str
    text: str
    score: float  # cosine similarity to the sub-query that selected it
    sub_query: str  # which sub-query retrieved it
    favicon: str | None = None

    @property
    def domain(self) -> str:
        return urlparse(self.url).netloc.removeprefix("www.")


class Claim(BaseModel):
    id: int  # 1-based, stable within one request
    text: str
    citation_ids: list[int]


Label = Literal["SUPPORTED", "PARTIAL", "UNSUPPORTED"]
Mode = Literal["strict", "lenient"]


class Verdict(BaseModel):
    claim_id: int
    label: Label
    evidence_span: str | None  # verbatim quote from a cited passage, checked in code
    rationale: str
    downgraded: bool = False  # SUPPORTED -> PARTIAL because the quote wasn't found


class Revision(BaseModel):
    claim_id: int
    action: Literal["rewritten", "removed"]
    new_text: str | None = None
    new_citation_ids: list[int] | None = None


def passes(label: Label, mode: Mode) -> bool:
    """strict: only SUPPORTED passes. lenient: PARTIAL passes too."""
    return label == "SUPPORTED" or (mode == "lenient" and label == "PARTIAL")
