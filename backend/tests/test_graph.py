from app.agents.planner import PlannerOutput, clean_queries
from app.agents.retriever import RetrieverConfig
from app.agents.reviser import ReviserOutput, RevisionOut
from app.agents.verifier import VerdictOut, VerifierOutput
from app.agents.writer import DraftClaim, WriterOutput
from app.graph import Agents, build_graph, run, stream_events
from app.services.embeddings import CachedEmbedder
from app.services.search import CachedSearch
from tests.fakes import FakeStructured, FakeTavily, bag_of_words_embed, page

EIFFEL = "The Eiffel Tower is 330 metres tall. It was completed in 1889 for the World's Fair."


def agents(tmp_path, verifier_outputs=(), reviser_outputs=()):
    return Agents(
        search=CachedSearch(
            FakeTavily({"eiffel tower height": [page("https://e.org", EIFFEL, "Eiffel")]}),
            tmp_path / "tavily",
        ),
        embedder=CachedEmbedder(bag_of_words_embed, tmp_path / "e.sqlite", "fake"),
        planner=FakeStructured(PlannerOutput(sub_queries=["eiffel tower height"])),
        writer=FakeStructured(
            WriterOutput(
                status="answered",
                claims=[
                    DraftClaim(text="The Eiffel Tower is 330 metres tall.", citation_ids=[1]),
                    DraftClaim(text="The Eiffel Tower is painted gold.", citation_ids=[1]),
                ],
                missing=None,
            )
        ),
        verifier=FakeStructured(*verifier_outputs),
        reviser=FakeStructured(*reviser_outputs),
        retriever_cfg=RetrieverConfig(),
    )


def v(claim_id, label, span=None):
    return VerdictOut(claim_id=claim_id, label=label, evidence_span=span, rationale="r")


FIRST_PASS = VerifierOutput(
    verdicts=[v(1, "SUPPORTED", "The Eiffel Tower is 330 metres tall."), v(2, "UNSUPPORTED")]
)


def test_full_flow_streams_events_in_order(tmp_path):
    graph = build_graph(
        agents(
            tmp_path,
            verifier_outputs=[FIRST_PASS],
            reviser_outputs=[ReviserOutput(decisions=[RevisionOut(claim_id=2, action="remove")])],
        )
    )
    events = list(stream_events(graph, "How tall is the Eiffel Tower?"))
    names = [e["event"] for e in events]

    stages = [(e["data"]["agent"], e["data"]["status"]) for e in events if e["event"] == "stage"]
    assert stages == [
        (a, s) for a in ["planner", "retriever", "writer", "verifier", "reviser"]
        for s in ["start", "done"]
    ]  # fmt: skip
    for kind in ["subqueries", "sources", "draft", "verdict", "revision", "final"]:
        assert kind in names
    assert names.index("subqueries") < names.index("sources") < names.index("draft")
    assert names.index("draft") < names.index("verdict") < names.index("revision")
    assert names[-1] == "final"

    final = events[-1]["data"]
    assert [c["id"] for c in final["claims"]] == [1]
    assert final["stats"]["removed"] == 1
    assert final["stats"]["supported"] == 1 and final["stats"]["unsupported"] == 1


def test_run_returns_state_with_timings_and_usage(tmp_path):
    graph = build_graph(
        agents(
            tmp_path,
            verifier_outputs=[FIRST_PASS],
            reviser_outputs=[ReviserOutput(decisions=[RevisionOut(claim_id=2, action="remove")])],
        )
    )
    state = run(graph, "How tall is the Eiffel Tower?")
    assert set(state["timings_ms"]) == {"planner", "retriever", "writer", "verifier", "reviser"}
    assert set(state["token_usage"]) == {"planner", "writer", "verifier", "reviser"}
    assert state["revision_count"] == 1
    assert [c.id for c in state["final_claims"]] == [1]


def test_verifier_off_keeps_draft_unchanged(tmp_path):
    graph = build_graph(agents(tmp_path))
    state = run(graph, "How tall?", verify_enabled=False)
    assert len(state["final_claims"]) == 2
    assert "verifier" not in state["timings_ms"]


def test_no_revision_removes_rejected_claims(tmp_path):
    graph = build_graph(agents(tmp_path, verifier_outputs=[FIRST_PASS]))
    events = list(stream_events(graph, "How tall?", allow_revision=False))
    assert "reviser" not in {e["data"].get("agent") for e in events if e["event"] == "stage"}
    assert [e["data"] for e in events if e["event"] == "revision"] == [
        {"claim_id": 2, "action": "removed"}
    ]
    assert events[-1]["data"]["stats"]["final_claims"] == 1


def test_all_supported_skips_reviser(tmp_path):
    all_good = VerifierOutput(
        verdicts=[
            v(1, "SUPPORTED", "The Eiffel Tower is 330 metres tall."),
            v(2, "SUPPORTED", "The Eiffel Tower is 330 metres tall."),
        ]
    )
    state = run(build_graph(agents(tmp_path, verifier_outputs=[all_good])), "How tall?")
    assert "reviser" not in state["timings_ms"]
    assert state["revisions"] == []


def test_clean_queries_dedupes_caps_and_falls_back():
    assert clean_queries([" a  b ", "A B", "c", "d", "e"], "q?", 3) == ["a b", "c", "d"]
    assert clean_queries(["", "  "], "q?", 3) == ["q?"]
