import pytest

from app.agents.llm import AgentOutputError, format_passages
from app.agents.writer import DraftClaim, WriterOutput, enforce_citations, write
from app.prompts import render
from tests.fakes import FakeStructured, make_passages

passages = make_passages


def FakeWriter(parsed, error=None):  # noqa: N802 - reads like the class it wraps
    return FakeStructured(parsed, error=error)


def output(*claims: tuple[str, list[int]], status: str = "answered") -> WriterOutput:
    return WriterOutput(
        status=status,
        claims=[DraftClaim(text=t, citation_ids=ids) for t, ids in claims],
        missing=None,
    )


def assert_every_claim_has_valid_citation(claims, valid_ids):
    for claim in claims:
        assert claim.citation_ids, f"claim {claim.id} has no citations"
        assert set(claim.citation_ids) <= valid_ids, f"claim {claim.id} cites unknown passages"


def test_every_claim_keeps_at_least_one_valid_citation():
    ps = passages(3)
    raw = output(
        ("Valid claim.", [1]),
        ("Mixed claim.", [2, 99]),  # 99 does not exist -> dropped, claim kept
        ("Hallucinated source.", [42]),  # nothing valid -> claim dropped
        ("No citations at all.", []),  # dropped
        ("Duplicate ids.", [3, 3, 1]),
    )
    result = enforce_citations(raw, ps)

    assert_every_claim_has_valid_citation(result.claims, {p.id for p in ps})
    assert [c.text for c in result.claims] == ["Valid claim.", "Mixed claim.", "Duplicate ids."]
    assert result.claims[1].citation_ids == [2]
    assert result.claims[2].citation_ids == [3, 1]
    assert [c.id for c in result.claims] == [1, 2, 3]  # renumbered after drops
    assert result.dropped_citations == 2  # 99 and 42
    assert result.dropped_claims == 2


def test_inline_markers_are_stripped_from_claim_text():
    result = enforce_citations(output(("LangGraph supports cycles [1, 2].", [1, 2])), passages())
    assert result.claims[0].text == "LangGraph supports cycles."


def test_all_claims_invalid_becomes_unanswerable():
    result = enforce_citations(output(("Made up.", [7])), passages())
    assert result.status == "unanswerable"
    assert result.claims == []


def test_write_prompt_contains_question_and_numbered_passages():
    fake = FakeWriter(output(("Claim.", [1])))
    result = write("What is X?", passages(2), fake)

    prompt = fake.prompts[0]
    assert "What is X?" in prompt
    assert "[1] Title 1 (site1.com)\nPassage 1 text." in prompt
    assert "[2] Title 2" in prompt
    assert result.usage == {"input_tokens": 100, "output_tokens": 20, "total_tokens": 120}


def test_no_passages_skips_llm_and_abstains():
    fake = FakeWriter(None)
    result = write("Anything?", [], fake)
    assert result.status == "unanswerable"
    assert fake.prompts == []


def test_parse_failure_raises():
    with pytest.raises(AgentOutputError):
        write("Q?", passages(), FakeWriter(None, error="bad json"))


def test_prompt_template_renders_without_leftover_placeholders():
    text = render("writer_v1", question="Q?", passages=format_passages(passages(1)))
    assert "$question" not in text and "$passages" not in text
