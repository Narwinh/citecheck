"""LangGraph wiring: planner -> retriever -> writer -> verifier -> [reviser] -> finalize.

Every node emits the SSE-shaped events from CLAUDE.md Section 5 through
LangGraph's custom stream (get_stream_writer), so the API layer only has to
forward them. `run()` ignores the events and returns the final state; the
eval harness uses that. `stream_events()` yields them; the API uses that.

Ablation switches live in the state: verify_enabled=False skips the verifier
and reviser (the "verifier off" baseline); allow_revision=False removes
rejected claims without trying to rewrite them.
"""

import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from functools import wraps
from typing import Annotated, Any, TypedDict

from langchain_core.runnables import Runnable
from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph

from app.agents.llm import add_usage
from app.agents.planner import plan
from app.agents.retriever import RetrieverConfig, retrieve
from app.agents.reviser import assemble_final, rejected_claims, revise_and_recheck
from app.agents.verifier import verify
from app.agents.writer import write
from app.services.embeddings import CachedEmbedder
from app.services.search import CachedSearch
from app.state import Claim, Mode, Passage, Revision, Verdict

SNIPPET_CHARS = 240


def _merge(a: dict, b: dict) -> dict:
    return {**a, **b}


def _merge_usage(a: dict, b: dict) -> dict:
    return {k: add_usage(a.get(k, {}), b.get(k, {})) for k in a.keys() | b.keys()}


class ResearchState(TypedDict, total=False):
    # inputs
    question: str
    mode: Mode
    verify_enabled: bool
    allow_revision: bool
    started_at: float
    # produced by agents
    sub_queries: list[str]
    passages: list[Passage]
    writer_status: str
    missing: str | None
    draft_claims: list[Claim]
    verdicts: list[Verdict]  # verifier's verdicts on the draft
    revisions: list[Revision]
    revision_count: int
    final_claims: list[Claim]
    final_verdicts: list[Verdict]
    stats: dict[str, Any]
    timings_ms: Annotated[dict[str, int], _merge]
    token_usage: Annotated[dict[str, dict[str, int]], _merge_usage]


@dataclass
class Agents:
    search: CachedSearch
    embedder: CachedEmbedder
    planner: Runnable
    writer: Runnable
    verifier: Runnable
    reviser: Runnable
    retriever_cfg: RetrieverConfig
    max_sub_queries: int = 4


def emit(event: str, data: dict[str, Any]) -> None:
    get_stream_writer()({"event": event, "data": data})


def timed(agent: str) -> Callable:
    """Wrap a node: emit stage start/done events and record its latency."""

    def decorate(node: Callable[[ResearchState], dict]) -> Callable[[ResearchState], dict]:
        @wraps(node)
        def wrapper(state: ResearchState) -> dict:
            emit("stage", {"agent": agent, "status": "start"})
            start = time.perf_counter()
            update = node(state)
            ms = round((time.perf_counter() - start) * 1000)
            emit("stage", {"agent": agent, "status": "done", "ms": ms})
            update["timings_ms"] = {agent: ms}
            return update

        return wrapper

    return decorate


def passage_card(p: Passage) -> dict[str, Any]:
    snippet = p.text if len(p.text) <= SNIPPET_CHARS else p.text[:SNIPPET_CHARS].rsplit(" ", 1)[0]
    return {
        "id": p.id,
        "url": p.url,
        "title": p.title,
        "domain": p.domain,
        "favicon": p.favicon,
        "snippet": snippet,
        "text": p.text,  # full passage, so the UI can highlight the evidence span in context
    }


def build_graph(agents: Agents):
    @timed("planner")
    def planner(state: ResearchState) -> dict:
        result = plan(state["question"], agents.planner, agents.max_sub_queries)
        emit("subqueries", {"items": result.sub_queries})
        return {"sub_queries": result.sub_queries, "token_usage": {"planner": result.usage}}

    @timed("retriever")
    def retriever(state: ResearchState) -> dict:
        result = retrieve(
            state["sub_queries"], agents.search, agents.embedder, agents.retriever_cfg
        )
        emit("sources", {"passages": [passage_card(p) for p in result.passages]})
        return {"passages": result.passages}

    @timed("writer")
    def writer(state: ResearchState) -> dict:
        result = write(state["question"], state["passages"], agents.writer)
        emit(
            "draft",
            {
                "status": result.status,
                "missing": result.missing,
                "claims": [c.model_dump() for c in result.claims],
            },
        )
        return {
            "writer_status": result.status,
            "missing": result.missing,
            "draft_claims": result.claims,
            "token_usage": {"writer": result.usage},
        }

    @timed("verifier")
    def verifier(state: ResearchState) -> dict:
        result = verify(state["draft_claims"], state["passages"], agents.verifier)
        for v in result.verdicts:
            emit("verdict", v.model_dump())
        return {"verdicts": result.verdicts, "token_usage": {"verifier": result.usage}}

    @timed("reviser")
    def reviser(state: ResearchState) -> dict:
        rejected = rejected_claims(state["draft_claims"], state["verdicts"], state["mode"])
        recheck = revise_and_recheck(
            state["question"],
            rejected,
            state["verdicts"],
            state["passages"],
            agents.verifier,
            agents.reviser,
            state["mode"],
        )
        for r in recheck.revisions:
            emit("revision", r.model_dump(exclude_none=True))
            if r.action == "rewritten":
                emit("verdict", recheck.rewrite_verdicts[r.claim_id].model_dump())
        final, final_verdicts = assemble_final(
            state["draft_claims"],
            state["verdicts"],
            recheck.revisions,
            recheck.rewrites,
            recheck.rewrite_verdicts,
        )
        return {
            "revisions": recheck.revisions,
            "revision_count": 1,
            "final_claims": final,
            "final_verdicts": final_verdicts,
            "token_usage": {
                "reviser": recheck.reviser_usage,
                "verifier": recheck.verifier_usage,
            },
        }

    def finalize(state: ResearchState) -> dict:
        update: dict[str, Any] = {}
        draft = state.get("draft_claims", [])
        verdicts = state.get("verdicts", [])
        revisions = state.get("revisions")

        if not state.get("verify_enabled", True):
            update |= {"final_claims": draft, "final_verdicts": [], "revisions": []}
        elif revisions is None:  # verified, but the reviser did not run
            rejected = rejected_claims(draft, verdicts, state["mode"])
            removals = [Revision(claim_id=c.id, action="removed") for c in rejected]
            for r in removals:
                emit("revision", r.model_dump(exclude_none=True))
            final, final_verdicts = assemble_final(draft, verdicts, removals, {}, {})
            update |= {
                "revisions": removals,
                "final_claims": final,
                "final_verdicts": final_verdicts,
            }

        final_claims = update.get("final_claims", state.get("final_claims", []))
        revisions = update.get("revisions", revisions or [])
        labels = [v.label for v in verdicts]
        tokens = sum(u.get("total_tokens", 0) for u in state.get("token_usage", {}).values())
        stats = {
            "claims": len(draft),
            "supported": labels.count("SUPPORTED"),
            "partial": labels.count("PARTIAL"),
            "unsupported": labels.count("UNSUPPORTED"),
            "revised": sum(r.action == "rewritten" for r in revisions),
            "removed": sum(r.action == "removed" for r in revisions),
            "final_claims": len(final_claims),
            "total_ms": round((time.perf_counter() - state["started_at"]) * 1000),
            "tokens": tokens,
        }
        emit(
            "final",
            {
                "status": state.get("writer_status", "unanswerable"),
                "missing": state.get("missing"),
                "claims": [c.model_dump() for c in final_claims],
                "stats": stats,
            },
        )
        return update | {"stats": stats}

    def after_writer(state: ResearchState) -> str:
        if state.get("verify_enabled", True) and state.get("draft_claims"):
            return "verifier"
        return "finalize"

    def after_verifier(state: ResearchState) -> str:
        if not state.get("allow_revision", True):
            return "finalize"
        rejected = rejected_claims(state["draft_claims"], state["verdicts"], state["mode"])
        return "reviser" if rejected else "finalize"

    graph = StateGraph(ResearchState)
    for name, node in [
        ("planner", planner),
        ("retriever", retriever),
        ("writer", writer),
        ("verifier", verifier),
        ("reviser", reviser),
        ("finalize", finalize),
    ]:
        graph.add_node(name, node)
    graph.add_edge(START, "planner")
    graph.add_edge("planner", "retriever")
    graph.add_edge("retriever", "writer")
    graph.add_conditional_edges("writer", after_writer, ["verifier", "finalize"])
    graph.add_conditional_edges("verifier", after_verifier, ["reviser", "finalize"])
    graph.add_edge("reviser", "finalize")
    graph.add_edge("finalize", END)
    return graph.compile()


def initial_state(
    question: str, mode: Mode = "strict", verify_enabled: bool = True, allow_revision: bool = True
) -> ResearchState:
    return {
        "question": question,
        "mode": mode,
        "verify_enabled": verify_enabled,
        "allow_revision": allow_revision,
        "started_at": time.perf_counter(),
        "revision_count": 0,
        "timings_ms": {},
        "token_usage": {},
    }


def run(graph, question: str, **options: Any) -> ResearchState:
    return graph.invoke(initial_state(question, **options))


def stream_events(graph, question: str, **options: Any) -> Iterator[dict[str, Any]]:
    """Yield {"event": ..., "data": ...} dicts in the order the agents produce them."""
    yield from graph.stream(initial_state(question, **options), stream_mode="custom")
