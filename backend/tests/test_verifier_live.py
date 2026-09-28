"""Hand-made verifier cases against the real Gemini model.

Run with:  pytest -m live
These cost a few thousand tokens and are skipped by default.
"""

import pytest

from app.agents.verifier import structured_verifier, verify
from app.config import get_settings
from app.services.factory import make_llm
from app.state import Claim, Passage

pytestmark = pytest.mark.live

PASSAGES = [
    Passage(
        id=1,
        url="https://example.org/eiffel",
        title="Eiffel Tower",
        text=(
            "The Eiffel Tower is a wrought-iron lattice tower on the Champ de Mars in Paris. "
            "It is 330 metres tall and was completed in 1889 as the entrance arch to the "
            "1889 World's Fair."
        ),
        score=0.8,
        sub_query="eiffel tower",
    ),
    Passage(
        id=2,
        url="https://example.org/wall",
        title="Great Wall of China",
        text=(
            "The Great Wall of China is a series of fortifications built across the northern "
            "borders of ancient Chinese states. Its main sections were built during the Ming "
            "dynasty."
        ),
        score=0.7,
        sub_query="great wall",
    ),
]

CLAIMS = [
    # Correct claim, correct citation.
    Claim(id=1, text="The Eiffel Tower is 330 metres tall.", citation_ids=[1]),
    # Deliberately wrong citation: true fact, but passage 2 is about the Great Wall.
    Claim(id=2, text="The Eiffel Tower was completed in 1889.", citation_ids=[2]),
    # True in the real world, absent from the cited passage: must not pass on model knowledge.
    Claim(
        id=3, text="The Eiffel Tower was designed by Gustave Eiffel's company.", citation_ids=[1]
    ),
    # Core supported, extra detail not: should be PARTIAL (or stricter).
    Claim(
        id=4,
        text=(
            "The Eiffel Tower is 330 metres tall and is the most visited paid monument "
            "in the world."
        ),
        citation_ids=[1],
    ),
]


@pytest.fixture(scope="module")
def verdicts():
    settings = get_settings()
    if settings.missing_keys():
        pytest.skip("API keys not configured")
    verifier = structured_verifier(make_llm(settings, settings.verifier_thinking_level))
    result = verify(CLAIMS, PASSAGES, verifier)
    return {v.claim_id: v for v in result.verdicts}


def test_correct_claim_is_supported_with_real_quote(verdicts):
    assert verdicts[1].label == "SUPPORTED"
    assert verdicts[1].evidence_span and "330" in verdicts[1].evidence_span


def test_wrong_citation_is_flagged(verdicts):
    assert verdicts[2].label == "UNSUPPORTED"


def test_world_knowledge_does_not_count_as_support(verdicts):
    assert verdicts[3].label == "UNSUPPORTED"


def test_extra_unsupported_detail_is_not_fully_supported(verdicts):
    assert verdicts[4].label in {"PARTIAL", "UNSUPPORTED"}
