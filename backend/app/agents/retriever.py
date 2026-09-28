"""Retriever agent: sub-queries -> ranked, deduplicated, numbered passages. No LLM call.

Selection is round-robin across sub-queries: each sub-query contributes its
next-best chunk in turn. Ranking everything by a single global score lets one
easy sub-query crowd out the others, which breaks multi-hop questions that
need evidence for every hop.
"""

from dataclasses import dataclass, field

from app.services.chunking import chunk_text
from app.services.embeddings import CachedEmbedder
from app.services.search import CachedSearch
from app.services.vectorstore import request_store
from app.state import Passage


@dataclass
class RetrieverConfig:
    top_k: int = 10
    max_chunks_per_url: int = 2  # keeps sources diverse
    duplicate_threshold: float = 0.95  # cosine similarity above this = same content
    max_page_chars: int = 12_000  # ~3k tokens per page; bounds embedding cost
    chunk_chars: int = 2400
    overlap_chars: int = 400


@dataclass
class Chunk:
    id: str
    url: str
    title: str
    text: str
    favicon: str | None


@dataclass
class RetrievalResult:
    passages: list[Passage]
    stats: dict[str, int] = field(default_factory=dict)


def build_chunks(
    search: CachedSearch, sub_queries: list[str], cfg: RetrieverConfig
) -> tuple[list[Chunk], int]:
    chunks: list[Chunk] = []
    seen_urls: set[str] = set()
    for query in sub_queries:
        for result in search.search(query):
            if result.url in seen_urls:  # same page from two sub-queries: chunk it once
                continue
            seen_urls.add(result.url)
            text = (result.raw_content or result.content)[: cfg.max_page_chars]
            for i, piece in enumerate(chunk_text(text, cfg.chunk_chars, cfg.overlap_chars)):
                chunks.append(
                    Chunk(f"{len(seen_urls)}-{i}", result.url, result.title, piece, result.favicon)
                )
    return chunks, len(seen_urls)


def select_round_robin(
    ranked: dict[str, list[tuple[str, float]]],
    chunks: dict[str, Chunk],
    vectors: dict[str, list[float]],
    cfg: RetrieverConfig,
) -> list[tuple[str, str, float]]:
    """Pick up to top_k (chunk_id, sub_query, score), one per sub-query per round."""
    selected: list[tuple[str, str, float]] = []
    per_url: dict[str, int] = {}
    cursors = {q: 0 for q in ranked}

    def acceptable(chunk_id: str) -> bool:
        if any(chunk_id == s for s, _, _ in selected):
            return False
        if per_url.get(chunks[chunk_id].url, 0) >= cfg.max_chunks_per_url:
            return False
        vec = vectors[chunk_id]
        return all(
            sum(a * b for a, b in zip(vec, vectors[s], strict=True)) < cfg.duplicate_threshold
            for s, _, _ in selected
        )

    while len(selected) < cfg.top_k and any(cursors[q] < len(ranked[q]) for q in ranked):
        for query, candidates in ranked.items():
            if len(selected) >= cfg.top_k:
                break
            while cursors[query] < len(candidates):
                chunk_id, score = candidates[cursors[query]]
                cursors[query] += 1
                if acceptable(chunk_id):
                    selected.append((chunk_id, query, score))
                    url = chunks[chunk_id].url
                    per_url[url] = per_url.get(url, 0) + 1
                    break
    return selected


def retrieve(
    sub_queries: list[str],
    search: CachedSearch,
    embedder: CachedEmbedder,
    cfg: RetrieverConfig | None = None,
) -> RetrievalResult:
    cfg = cfg or RetrieverConfig()
    chunks, n_pages = build_chunks(search, sub_queries, cfg)
    if not chunks:
        return RetrievalResult([], {"pages": 0, "chunks": 0})

    chunk_vectors = embedder.embed([c.text for c in chunks], "RETRIEVAL_DOCUMENT")
    query_vectors = embedder.embed(sub_queries, "RETRIEVAL_QUERY")
    vectors = {c.id: v for c, v in zip(chunks, chunk_vectors, strict=True)}
    by_id = {c.id: c for c in chunks}

    with request_store() as store:
        store.add(list(vectors), list(vectors.values()))
        ranked = {
            q: store.query(v, n=len(chunks))
            for q, v in zip(sub_queries, query_vectors, strict=True)
        }

    picks = select_round_robin(ranked, by_id, vectors, cfg)
    passages = [
        Passage(
            id=n,
            url=by_id[cid].url,
            title=by_id[cid].title,
            text=by_id[cid].text,
            score=round(score, 4),
            sub_query=query,
            favicon=by_id[cid].favicon,
        )
        for n, (cid, query, score) in enumerate(picks, start=1)
    ]
    return RetrievalResult(passages, {"pages": n_pages, "chunks": len(chunks)})
