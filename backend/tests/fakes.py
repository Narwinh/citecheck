"""Offline stand-ins for Tavily and Gemini embeddings."""

import hashlib
import re
from typing import Any

from app.services.embeddings import TaskType, normalize

DIMS = 64


class FakeTavily:
    def __init__(self, pages: dict[str, list[dict[str, Any]]]):
        self.pages = pages  # query -> list of Tavily-shaped results
        self.calls: list[str] = []

    def search(self, query: str, **params: Any) -> dict[str, Any]:
        self.calls.append(query)
        return {"query": query, "results": self.pages.get(query, [])}


def bag_of_words_embed(texts: list[str], task: TaskType) -> list[list[float]]:
    """Deterministic embedding: hashed word counts. Similar words -> similar vectors."""
    out = []
    for text in texts:
        vec = [0.0] * DIMS
        for word in re.findall(r"[a-z]+", text.lower()):
            vec[int(hashlib.md5(word.encode()).hexdigest(), 16) % DIMS] += 1.0
        out.append(normalize(vec))
    return out


def page(url: str, text: str, title: str | None = None) -> dict[str, Any]:
    return {"url": url, "title": title or url, "content": text[:100], "raw_content": text}
