"""Stage 4 CLI: retrieve -> write -> verify -> revise once -> print verdicts.

Usage (from backend/):
    python scripts/verify.py "question" [--sub-query "..."]... [--mode lenient]
"""

import argparse
import sys
import time

from app.agents.retriever import RetrieverConfig, retrieve
from app.agents.reviser import structured_reviser, verify_and_revise
from app.agents.verifier import structured_verifier
from app.agents.writer import structured_writer, write
from app.config import get_settings
from app.services.factory import make_embedder, make_llm, make_search

MARKS = {"SUPPORTED": "OK ", "PARTIAL": "~  ", "UNSUPPORTED": "X  "}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("question")
    parser.add_argument("--sub-query", action="append", dest="sub_queries")
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--mode", choices=["strict", "lenient"], default="strict")
    args = parser.parse_args()

    s = get_settings()
    if missing := s.missing_keys():
        print(f"Missing {', '.join(missing)} in .env")
        return 1

    timings: dict[str, float] = {}
    t = time.perf_counter()
    retrieval = retrieve(
        args.sub_queries or [args.question],
        make_search(s),
        make_embedder(s),
        RetrieverConfig(top_k=args.top_k),
    )
    timings["retrieve"] = time.perf_counter() - t

    t = time.perf_counter()
    draft = write(
        args.question, retrieval.passages, structured_writer(make_llm(s, s.writer_thinking_level))
    )
    timings["write"] = time.perf_counter() - t

    t = time.perf_counter()
    check = verify_and_revise(
        args.question,
        draft.claims,
        retrieval.passages,
        structured_verifier(make_llm(s, s.verifier_thinking_level)),
        structured_reviser(make_llm(s, s.reviser_thinking_level)),
        mode=args.mode,
    )
    timings["verify+revise"] = time.perf_counter() - t

    print(f"Draft ({draft.status}), verified in {args.mode} mode\n")
    for claim, verdict in zip(draft.claims, check.draft_verdicts, strict=True):
        cites = "".join(f"[{i}]" for i in claim.citation_ids)
        print(f"{MARKS[verdict.label]}{claim.id}. {claim.text} {cites}")
        print(f"     {verdict.label}: {verdict.rationale}")
        if verdict.evidence_span:
            print(f'     evidence: "{verdict.evidence_span}"')

    if check.revisions:
        print("\nRevisions")
        for r in check.revisions:
            if r.action == "rewritten":
                cites = "".join(f"[{i}]" for i in r.new_citation_ids or [])
                print(f"  {r.claim_id}. rewritten -> {r.new_text} {cites}")
            else:
                print(f"  {r.claim_id}. removed")

    print("\nFinal answer")
    for claim in check.final_claims:
        print(f"  {claim.text} {''.join(f'[{i}]' for i in claim.citation_ids)}")

    labels = [v.label for v in check.draft_verdicts]
    print(
        f"\ndraft: {len(labels)} claims · {labels.count('SUPPORTED')} supported · "
        f"{labels.count('PARTIAL')} partial · {labels.count('UNSUPPORTED')} unsupported"
    )
    print(f"final: {len(check.final_claims)} claims")
    print(f"usage: writer {draft.usage} · {check.usage}")
    print(" · ".join(f"{k} {v:.1f}s" for k, v in timings.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
