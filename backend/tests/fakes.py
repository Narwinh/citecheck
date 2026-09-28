"""Offline stand-ins for Tavily and Gemini embeddings."""

import hashlib
import re
from typing import Any

from langchain_core.messages import AIMessage

from app.services.embeddings import TaskType, normalize
from app.state import Passage

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


class FakeStructured:
    """Mimics llm.with_structured_output(..., include_raw=True); returns outputs in order."""

    def __init__(self, *outputs: Any, error: str | None = None):
        self.outputs = list(outputs)
        self.error = error
        self.prompts: list[str] = []

    def invoke(self, prompt: str) -> dict:
        self.prompts.append(prompt)
        parsed = self.outputs.pop(0) if self.outputs else None
        raw = AIMessage(
            content="{}",
            usage_metadata={"input_tokens": 100, "output_tokens": 20, "total_tokens": 120},
        )
        return {"raw": raw, "parsed": parsed, "parsing_error": self.error}


def make_passages(n: int = 3) -> list[Passage]:
    return [
        Passage(
            id=i,
            url=f"https://www.site{i}.com/page",
            title=f"Title {i}",
            text=f"Passage {i} text.",
            score=0.8,
            sub_query="q",
        )
        for i in range(1, n + 1)
    ]
