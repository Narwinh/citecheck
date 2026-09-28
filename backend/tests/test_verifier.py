from app.agents.reviser import ReviserOutput, RevisionOut, verify_and_revise
from app.agents.verifier import VerdictOut, VerifierOutput, span_in_passages, verify
from app.state import Claim, Passage, passes
from tests.fakes import FakeStructured

EIFFEL = Passage(
    id=1,
    url="https://example.org/eiffel",
    title="Eiffel Tower",
    text="The Eiffel Tower is 330 metres tall. It was completed in 1889 for the World’s Fair.",
    score=0.8,
    sub_query="q",
)
WALL = Passage(
    id=2,
    url="https://example.org/wall",
    title="Great Wall",
    text="The Great Wall of China stretches across northern China.",
    score=0.7,
    sub_query="q",
)
PASSAGES = [EIFFEL, WALL]


def v(claim_id, label, span=None, rationale="r"):
    return VerdictOut(claim_id=claim_id, label=label, evidence_span=span, rationale=rationale)


def test_mode_rules():
    assert passes("SUPPORTED", "strict") and passes("SUPPORTED", "lenient")
    assert not passes("PARTIAL", "strict") and passes("PARTIAL", "lenient")
    assert not passes("UNSUPPORTED", "strict") and not passes("UNSUPPORTED", "lenient")


def test_span_matching_tolerates_case_whitespace_quotes_and_ellipsis():
    assert span_in_passages("the eiffel tower is   330 metres tall.", [EIFFEL])
    assert span_in_passages("for the World's Fair", [EIFFEL])  # straight vs curly quote
    assert span_in_passages("The Eiffel Tower ... completed in 1889", [EIFFEL])
    assert not span_in_passages("The Eiffel Tower is 300 metres tall.", [WALL])
    assert not span_in_passages("completely invented sentence about towers", [EIFFEL])


def test_verifier_only_sees_cited_passages():
    fake = FakeStructured(VerifierOutput(verdicts=[v(1, "SUPPORTED", "330 metres tall")]))
    verify([Claim(id=1, text="It is 330 m.", citation_ids=[1])], PASSAGES, fake)
    assert "Eiffel Tower is 330" in fake.prompts[0]
    assert "Great Wall" not in fake.prompts[0]


def test_supported_without_findable_quote_is_downgraded():
    claims = [Claim(id=1, text="The tower is 330 m tall.", citation_ids=[1])]
    fake = FakeStructured(VerifierOutput(verdicts=[v(1, "SUPPORTED", "a quote not in the text")]))
    verdict = verify(claims, PASSAGES, fake).verdicts[0]
    assert verdict.label == "PARTIAL"
    assert verdict.downgraded
    assert verdict.evidence_span is None


def test_missing_verdict_counts_as_unsupported():
    claims = [Claim(id=1, text="a", citation_ids=[1]), Claim(id=2, text="b", citation_ids=[2])]
    fake = FakeStructured(VerifierOutput(verdicts=[v(1, "SUPPORTED", "330 metres tall")]))
    verdicts = verify(claims, PASSAGES, fake).verdicts
    assert [x.label for x in verdicts] == ["SUPPORTED", "UNSUPPORTED"]


def draft_claims():
    return [
        Claim(id=1, text="The Eiffel Tower is 330 metres tall.", citation_ids=[1]),
        Claim(id=2, text="The Eiffel Tower was completed in 1889.", citation_ids=[2]),  # wrong
        Claim(id=3, text="The Eiffel Tower is painted gold.", citation_ids=[1]),  # unsupported
    ]


def test_wrong_citation_is_rewritten_and_unfixable_claim_removed():
    verifier = FakeStructured(
        VerifierOutput(
            verdicts=[
                v(1, "SUPPORTED", "The Eiffel Tower is 330 metres tall."),
                v(2, "UNSUPPORTED"),
                v(3, "UNSUPPORTED"),
            ]
        ),
        VerifierOutput(verdicts=[v(2, "SUPPORTED", "It was completed in 1889")]),
    )
    reviser = FakeStructured(
        ReviserOutput(
            decisions=[
                RevisionOut(
                    claim_id=2,
                    action="rewrite",
                    text="The Eiffel Tower was completed in 1889.",
                    citation_ids=[1],
                ),
                RevisionOut(claim_id=3, action="remove"),
            ]
        )
    )
    result = verify_and_revise("How tall?", draft_claims(), PASSAGES, verifier, reviser)

    assert [x.label for x in result.draft_verdicts] == ["SUPPORTED", "UNSUPPORTED", "UNSUPPORTED"]
    assert [(r.claim_id, r.action) for r in result.revisions] == [(2, "rewritten"), (3, "removed")]
    assert [(c.id, c.citation_ids) for c in result.final_claims] == [(1, [1]), (2, [1])]
    assert all(x.label == "SUPPORTED" for x in result.final_verdicts)
    assert "Claim 3" not in verifier.prompts[1]  # only the rewrite is re-verified


def test_rewrite_that_fails_reverification_is_removed():
    verifier = FakeStructured(
        VerifierOutput(
            verdicts=[
                v(1, "SUPPORTED", "330 metres tall"),
                v(2, "UNSUPPORTED"),
                v(3, "SUPPORTED", "330 metres tall"),
            ]
        ),  # fmt: skip
        VerifierOutput(verdicts=[v(2, "PARTIAL", "completed in 1889")]),
    )
    reviser = FakeStructured(
        ReviserOutput(
            decisions=[RevisionOut(claim_id=2, action="rewrite", text="x", citation_ids=[1])]
        )
    )
    result = verify_and_revise("Q", draft_claims(), PASSAGES, verifier, reviser, mode="strict")
    assert [(r.claim_id, r.action) for r in result.revisions] == [(2, "removed")]
    assert [c.id for c in result.final_claims] == [1, 3]


def test_lenient_mode_keeps_partial_without_revising():
    verifier = FakeStructured(
        VerifierOutput(
            verdicts=[
                v(1, "SUPPORTED", "330 metres tall"),
                v(2, "PARTIAL", "1889"),
                v(3, "PARTIAL", "1889"),
            ]
        ),  # fmt: skip
    )
    reviser = FakeStructured()
    result = verify_and_revise("Q", draft_claims(), PASSAGES, verifier, reviser, mode="lenient")
    assert result.revisions == []
    assert reviser.prompts == []
    assert len(result.final_claims) == 3


def test_revision_disabled_removes_rejected_claims():
    verifier = FakeStructured(
        VerifierOutput(
            verdicts=[
                v(1, "SUPPORTED", "330 metres tall"),
                v(2, "UNSUPPORTED"),
                v(3, "UNSUPPORTED"),
            ]
        ),  # fmt: skip
    )
    result = verify_and_revise(
        "Q", draft_claims(), PASSAGES, verifier, FakeStructured(), allow_revision=False
    )
    assert [c.id for c in result.final_claims] == [1]
    assert {r.action for r in result.revisions} == {"removed"}
