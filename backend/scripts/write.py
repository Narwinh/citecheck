"""Stage 3 CLI: question -> retrieve -> writer claims with citations.

Usage (from backend/):
    python scripts/write.py "question" [--sub-query "..."]...
"""

import argparse
import sys
import time

from app.agents.retriever import RetrieverConfig, retrieve
from app.agents.writer import structured_writer, write
from app.config import get_settings
from app.services.factory import make_embedder, make_llm, make_search


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

    start = time.perf_counter()
    retrieval = retrieve(
        args.sub_queries or [args.question],
        make_search(settings),
        make_embedder(settings),
        RetrieverConfig(top_k=args.top_k),
    )
    retrieve_ms = (time.perf_counter() - start) * 1000

    print("Sources")
    for p in retrieval.passages:
        print(f"  [{p.id}] {p.domain} · {p.title}")

    start = time.perf_counter()
    writer = structured_writer(make_llm(settings, settings.writer_thinking_level))
    result = write(args.question, retrieval.passages, writer)
    write_ms = (time.perf_counter() - start) * 1000

    print(f"\nAnswer ({result.status})")
    for c in result.claims:
        cites = "".join(f"[{i}]" for i in c.citation_ids)
        print(f"  {c.id}. {c.text} {cites}")
    if result.missing:
        print(f"\nNot covered by sources: {result.missing}")

    print(
        f"\nretrieve {retrieve_ms:.0f} ms · write {write_ms:.0f} ms · "
        f"tokens {result.usage} · dropped citations {result.dropped_citations}, "
        f"dropped claims {result.dropped_claims}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
