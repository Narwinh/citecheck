"""Stage 2 CLI: question -> numbered passages with URLs.

Usage (from backend/):
    python scripts/retrieve.py "Who won the 2026 Tour de France?"
    python scripts/retrieve.py "question" --sub-query "hop one" --sub-query "hop two"

Until the planner exists (Stage 5), the question itself is the only sub-query
unless you pass --sub-query. Run the same command twice to see cache hits.
"""

import argparse
import sys
import textwrap
import time

from app.agents.retriever import RetrieverConfig, retrieve
from app.config import get_settings
from app.services.factory import make_embedder, make_search


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("question")
    parser.add_argument("--sub-query", action="append", dest="sub_queries")
    parser.add_argument("--top-k", type=int, default=10)
    args = parser.parse_args()

    settings = get_settings()
    if missing := settings.missing_keys():
        print(f"Missing {', '.join(missing)} in .env")
        return 1

    search, embedder = make_search(settings), make_embedder(settings)
    sub_queries = args.sub_queries or [args.question]

    start = time.perf_counter()
    result = retrieve(sub_queries, search, embedder, RetrieverConfig(top_k=args.top_k))
    elapsed_ms = (time.perf_counter() - start) * 1000

    for p in result.passages:
        print(f"\n[{p.id}] {p.title}")
        print(f"    {p.url}")
        print(f"    score {p.score:.3f} · via {p.sub_query!r} · {len(p.text)} chars")
        print(textwrap.indent(textwrap.shorten(p.text, 300), "    "))

    print(
        f"\n{len(result.passages)} passages from {result.stats['pages']} pages "
        f"({result.stats['chunks']} chunks) in {elapsed_ms:.0f} ms"
    )
    print(f"tavily cache: {search.hits} hit / {search.misses} miss")
    print(f"embedding cache: {embedder.hits} hit / {embedder.misses} miss")
    return 0


if __name__ == "__main__":
    sys.exit(main())
