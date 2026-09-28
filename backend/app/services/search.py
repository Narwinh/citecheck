"""Tavily web search with a JSON disk cache.

The cache key covers the query and every search parameter, so changing
max_results or search_depth never serves a stale shape. Cached files are
plain JSON, which makes eval runs reproducible and inspectable by hand.
"""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from tavily import TavilyClient


@dataclass
class SearchResult:
    url: str
    title: str
    content: str  # Tavily's query-focused snippet
    raw_content: str | None  # full page text, when Tavily could extract it
    favicon: str | None


class SearchBackend(Protocol):
    def search(self, query: str, **params: Any) -> dict[str, Any]: ...


class CachedSearch:
    def __init__(
        self,
        client: SearchBackend,
        cache_dir: Path,
        max_results: int = 5,
        search_depth: str = "basic",
    ):
        self.client = client
        self.cache_dir = cache_dir
        self.params = {
            "max_results": max_results,
            "search_depth": search_depth,
            "include_raw_content": "text",
            "include_favicon": True,
        }
        self.hits = 0
        self.misses = 0

    @classmethod
    def from_api_key(cls, api_key: str, cache_dir: Path, **kwargs: Any) -> "CachedSearch":
        return cls(TavilyClient(api_key=api_key), cache_dir, **kwargs)

    def _cache_path(self, query: str) -> Path:
        key = json.dumps({"query": query.strip().lower(), **self.params}, sort_keys=True)
        return self.cache_dir / f"{hashlib.sha256(key.encode()).hexdigest()[:24]}.json"

    def search(self, query: str) -> list[SearchResult]:
        path = self._cache_path(query)
        if path.is_file():
            self.hits += 1
            response = json.loads(path.read_text(encoding="utf-8"))["response"]
        else:
            self.misses += 1
            response = self.client.search(query, **self.params)
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            tmp.write_text(
                json.dumps({"query": query, "params": self.params, "response": response}),
                encoding="utf-8",
            )
            tmp.replace(path)  # atomic, so an interrupted run never leaves half a file
        return [
            SearchResult(
                url=r["url"],
                title=r.get("title") or r["url"],
                content=r.get("content") or "",
                raw_content=r.get("raw_content"),
                favicon=r.get("favicon"),
            )
            for r in response.get("results", [])
        ]
