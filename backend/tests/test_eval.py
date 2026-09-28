import json
import sys
from pathlib import Path

import pytest

EVAL_DIR = Path(__file__).resolve().parents[2] / "eval"
sys.path.insert(0, str(EVAL_DIR))

import metrics  # noqa: E402
import run_eval  # noqa: E402
from app.agents.llm import AllModelsFailed  # noqa: E402
from app.state import Claim, Passage, Verdict  # noqa: E402
from judge import CitationJudgment, ClaimJudgment, JudgeOutput, judge  # noqa: E402
from tests.fakes import FakeStructured, make_passages  # noqa: E402


def record(**overrides):
    """3 draft claims: 1 SUPPORTED, 2 PARTIAL, 3 UNSUPPORTED; claim 3 rewritten (PARTIAL)."""
    base = {
        "id": "q1",
        "category": "factual",
        "status": "ok",
        "writer_status": "answered",
        "draft_claims": [
            {"id": 1, "text": "a", "citation_ids": [1]},
            {"id": 2, "text": "b", "citation_ids": [1, 2]},
            {"id": 3, "text": "c", "citation_ids": [2]},
        ],
        "verdicts": [
            {"claim_id": 1, "label": "SUPPORTED"},
            {"claim_id": 2, "label": "PARTIAL"},
            {"claim_id": 3, "label": "UNSUPPORTED"},
        ],
        "rewrite_attempts": [
            {"claim": {"id": 3, "text": "c2", "citation_ids": [1]}, "verdict": {"label": "PARTIAL"}}
        ],
        "judge": {
            "d1": {"label": "SUPPORTED", "citations": {"1": True}},
            "d2": {"label": "PARTIAL", "citations": {"1": True, "2": False}},
            "d3": {"label": "UNSUPPORTED", "citations": {"2": False}},
            "r3": {"label": "SUPPORTED", "citations": {"1": True}},
        },
        "timings_ms": {"writer": 1000, "verifier": 500},
        "token_usage": {"writer": {"total_tokens": 100, "calls:m1": 1}},
        "total_ms": 2000,
    }
    return base | overrides


def test_variant_keys_cover_every_ablation():
    r = record()
    assert metrics.variant_keys(r, "off") == ["d1", "d2", "d3"]
    assert metrics.variant_keys(r, "remove_strict") == ["d1"]
    assert metrics.variant_keys(r, "remove_lenient") == ["d1", "d2"]
    assert metrics.variant_keys(r, "revise_strict") == ["d1"]  # rewrite only PARTIAL
    assert metrics.variant_keys(r, "revise_lenient") == ["d1", "d2", "r3"]


def test_claim_metrics_before_and_after():
    off = metrics.claim_metrics([record()], "off")
    assert off["unsupported_rate"] == pytest.approx(1 / 3, abs=1e-3)
    assert off["citation_precision"] == pytest.approx(2 / 4)
    strict = metrics.claim_metrics([record()], "revise_strict")
    assert strict["unsupported_rate"] == 0 and strict["removal_rate"] == pytest.approx(2 / 3, 1e-3)


def test_abstention_counts_empty_answers_on_unanswerable():
    abstained = record(
        id="u1",
        category="unanswerable",
        writer_status="unanswerable",
        draft_claims=[],
        verdicts=[],
        judge={},
    )
    answered = record(id="u2", category="unanswerable")
    out = metrics.abstention_metrics([abstained, answered, record()])
    assert out["off"]["correct_abstentions"] == 0.5
    assert out["off"]["false_abstentions"] == 0.0


def test_kappa_and_agreement():
    perfect = [("SUPPORTED", "SUPPORTED"), ("PARTIAL", "PARTIAL"), ("UNSUPPORTED", "UNSUPPORTED")]
    assert metrics.cohens_kappa(perfect) == 1.0
    a = metrics.agreement([("SUPPORTED", "SUPPORTED"), ("SUPPORTED", "PARTIAL")])
    assert a["exact"] == 0.5 and a["pass_fail"] == 0.5


def test_judge_vs_human_uses_matching_keys():
    human = [
        {"question_id": "q1", "key": "d2", "label": "PARTIAL"},
        {"question_id": "q1", "key": "d3", "label": "PARTIAL"},
    ]
    out = metrics.judge_vs_human([record()], human)
    assert out["n"] == 2 and out["exact"] == 0.5


def test_question_rows_count_before_and_after():
    row = metrics.question_rows([record(revisions=[{"claim_id": 3, "action": "removed"}])])[0]
    assert row["draft_claims"] == 3 and row["final_claims"] == 1
    assert row["unsupported_before"] == 1 and row["unsupported_after"] == 0
    assert row["removed"] == 1 and row["models"] == ["m1"]


def test_percentile_interpolates():
    assert metrics.percentile([1, 2, 3, 4], 0.5) == 2.5
    assert metrics.percentile([], 0.5) is None


def test_judge_marks_skipped_items_unlabeled():
    from judge import JudgeItem

    items = [
        JudgeItem(key="d1", text="x", citation_ids=[1]),
        JudgeItem(key="d2", text="y", citation_ids=[2]),
    ]
    cite = CitationJudgment(passage_id=1, supports=True)
    out = JudgeOutput(judgments=[ClaimJudgment(key="d1", label="SUPPORTED", citations=[cite])])
    labels, _ = judge(items, make_passages(2), FakeStructured(out))
    assert labels["d1"] == {"label": "SUPPORTED", "citations": {1: True}}
    assert labels["d2"]["label"] is None


# ---------- run_benchmark with a fake graph ----------


class FakeGraph:
    def __init__(self, fail_ids=(), quota_after=None):
        self.fail_ids, self.quota_after, self.calls = set(fail_ids), quota_after, 0

    def invoke(self, state):
        self.calls += 1
        if self.quota_after is not None and self.calls > self.quota_after:
            raise AllModelsFailed([RuntimeError("429 RESOURCE_EXHAUSTED PerDay")])
        if state["question"] in self.fail_ids:
            raise ValueError("boom")
        p = make_passages(1)
        return {
            "writer_status": "answered",
            "passages": p,
            "draft_claims": [Claim(id=1, text="t", citation_ids=[1])],
            "verdicts": [Verdict(claim_id=1, label="SUPPORTED", evidence_span="x", rationale="r")],
            "rewrite_attempts": [],
            "revisions": [],
            "final_claims": [Claim(id=1, text="t", citation_ids=[1])],
            "timings_ms": {"writer": 5},
            "token_usage": {},
            "stats": {"total_ms": 10},
        }


def judge_llm():
    out = JudgeOutput(judgments=[ClaimJudgment(key="d1", label="SUPPORTED", citations=[])])
    return FakeStructured(*[out] * 10)


ITEMS = [{"id": f"q{i}", "question": f"Q{i}", "category": "factual"} for i in range(3)]


def test_run_benchmark_resumes_and_retries_errors(tmp_path):
    out, full = tmp_path / "out", tmp_path / "full"
    run_eval.run_benchmark(ITEMS, FakeGraph(fail_ids={"Q1"}), judge_llm(), out, full)
    results = run_eval.load_results(out / "results.jsonl")
    assert {k: v["status"] for k, v in results.items()} == {"q0": "ok", "q1": "error", "q2": "ok"}

    graph = FakeGraph()
    run_eval.run_benchmark(ITEMS, graph, judge_llm(), out, full)
    assert graph.calls == 1  # only the failed question reran
    assert all(r["status"] == "ok" for r in run_eval.load_results(out / "results.jsonl").values())


def test_run_benchmark_stops_cleanly_on_daily_quota(tmp_path):
    out = tmp_path / "out"
    finished = run_eval.run_benchmark(ITEMS, FakeGraph(quota_after=1), judge_llm(), out, tmp_path)
    assert finished is False
    assert list(run_eval.load_results(out / "results.jsonl")) == ["q0"]


def test_committed_record_has_snippets_not_full_text(tmp_path):
    run_eval.run_benchmark(ITEMS[:1], FakeGraph(), judge_llm(), tmp_path / "o", tmp_path / "f")
    rec = run_eval.load_results(tmp_path / "o" / "results.jsonl")["q0"]
    assert "snippet" in rec["passages"][0] and "text" not in rec["passages"][0]
    full = json.loads((tmp_path / "f" / "q0.json").read_text())
    assert Passage(**full[0]).text == "Passage 1 text."
