"""Stage 5 CLI: the full LangGraph pipeline, printing events as they stream.

Usage (from backend/):
    python scripts/ask.py "question" [--mode lenient] [--no-verify] [--no-revise]
"""

import argparse
import sys

from app.config import get_settings
from app.graph import build_graph, stream_events
from app.services.factory import make_agents

MARKS = {"SUPPORTED": "OK", "PARTIAL": "~ ", "UNSUPPORTED": "X "}


def show(event: str, data: dict) -> None:
    if event == "stage":
        if data["status"] == "start":
            print(f"\n-- {data['agent']} ...")
        else:
            print(f"   {data['agent']} done in {data['ms']} ms")
    elif event == "subqueries":
        for q in data["items"]:
            print(f"   sub-query: {q}")
    elif event == "sources":
        for p in data["passages"]:
            print(f"   [{p['id']}] {p['domain']} · {p['title'][:70]}")
    elif event == "draft":
        print(f"   status: {data['status']}")
        for c in data["claims"]:
            print(f"   {c['id']}. {c['text']} {''.join(f'[{i}]' for i in c['citation_ids'])}")
    elif event == "verdict":
        mark, label = MARKS[data["label"]], data["label"]
        print(f"   {mark} claim {data['claim_id']}: {label} - {data['rationale']}")
    elif event == "revision":
        detail = f" -> {data['new_text']}" if data["action"] == "rewritten" else ""
        print(f"   claim {data['claim_id']} {data['action']}{detail}")
    elif event == "final":
        print("\n== Final answer")
        for c in data["claims"]:
            print(f"   {c['text']} {''.join(f'[{i}]' for i in c['citation_ids'])}")
        if data["missing"]:
            print(f"   (not covered: {data['missing']})")
        s = data["stats"]
        print(
            f"\n{s['claims']} claims · {s['supported']} supported · {s['partial']} partial · "
            f"{s['unsupported']} unsupported · {s['revised']} revised · {s['removed']} removed · "
            f"{s['total_ms'] / 1000:.1f}s · {s['tokens']} tokens"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("question")
    parser.add_argument("--mode", choices=["strict", "lenient"], default="strict")
    parser.add_argument("--no-verify", action="store_true")
    parser.add_argument("--no-revise", action="store_true")
    args = parser.parse_args()

    settings = get_settings()
    if missing := settings.missing_keys():
        print(f"Missing {', '.join(missing)} in .env")
        return 1

    graph = build_graph(make_agents(settings))
    for chunk in stream_events(
        graph,
        args.question[: settings.max_question_chars],
        mode=args.mode,
        verify_enabled=not args.no_verify,
        allow_revision=not args.no_revise,
    ):
        show(chunk["event"], chunk["data"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
