"""Shared data models passed between agents."""

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
