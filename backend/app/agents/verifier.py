"""Verifier agent: label each claim against ONLY the passages it cites.

All claims go in one batched call. Each claim is shown with its citation IDs,
and only the cited passages are included, so the model cannot lean on an
uncited source.

The verifier must quote its evidence. We check that quote against the cited
passage text in code: a SUPPORTED verdict whose quote cannot be found is
downgraded to PARTIAL. A verdict that cannot show where its support is
should not count as fully supported.
"""

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any

from langchain_core.runnables import Runnable
from pydantic import BaseModel, Field

from app.agents.llm import format_passages, invoke_structured, structured
from app.prompts import render
from app.state import Claim, Label, Passage, Verdict

PROMPT = "verifier_v1"
FUZZY_MATCH_MIN = 0.9  # share of the quote that must appear contiguously in the passage


class VerdictOut(BaseModel):
    claim_id: int
    label: Label
    evidence_span: str | None = Field(description="Verbatim excerpt from a cited passage.")
    rationale: str


class VerifierOutput(BaseModel):
    verdicts: list[VerdictOut]


@dataclass
class VerifyResult:
    verdicts: list[Verdict]
    usage: dict[str, int] = field(default_factory=dict)


def structured_verifier(llm: Any) -> Runnable:
    return structured(llm, VerifierOutput)


_QUOTES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-"})


def _normalize(text: str) -> str:
    return " ".join(text.translate(_QUOTES).lower().split())


def span_in_passages(span: str, passages: list[Passage]) -> bool:
    """True if every piece of the quote (split on ellipses) appears in one cited passage."""
    pieces = [_normalize(p) for p in re.split(r"\.\.\.|…", span)]
    pieces = [p for p in pieces if p]
    if not pieces:
        return False
    for passage in passages:
        haystack = _normalize(passage.text)
        if all(p in haystack or _fuzzy_contains(p, haystack) for p in pieces):
            return True
    return False


def _fuzzy_contains(needle: str, haystack: str) -> bool:
    match = SequenceMatcher(None, haystack, needle, autojunk=False).find_longest_match()
    return match.size >= FUZZY_MATCH_MIN * len(needle)


def format_claims(claims: list[Claim]) -> str:
    return "\n".join(
        f"Claim {c.id}: {c.text}\nCites: {', '.join(f'[{i}]' for i in c.citation_ids)}"
        for c in claims
    )


def check_verdicts(
    output: VerifierOutput, claims: list[Claim], passages: list[Passage]
) -> list[Verdict]:
    by_id = {p.id: p for p in passages}
    returned: dict[int, VerdictOut] = {}
    for v in output.verdicts:
        returned.setdefault(v.claim_id, v)  # first verdict wins if the model repeats one

    verdicts = []
    for claim in claims:
        out = returned.get(claim.id)
        if out is None:
            verdicts.append(
                Verdict(
                    claim_id=claim.id,
                    label="UNSUPPORTED",
                    evidence_span=None,
                    rationale="The verifier returned no verdict for this claim.",
                )
            )
            continue

        cited = [by_id[i] for i in claim.citation_ids if i in by_id]
        span = (out.evidence_span or "").strip() or None
        span_found = span is not None and span_in_passages(span, cited)
        label, downgraded, rationale = out.label, False, out.rationale
        if label == "SUPPORTED" and not span_found:
            label, downgraded = "PARTIAL", True
            rationale = f"{rationale} (Downgraded: quoted evidence not found in the cited passage.)"
        verdicts.append(
            Verdict(
                claim_id=claim.id,
                label=label,
                evidence_span=span if span_found else None,
                rationale=rationale,
                downgraded=downgraded,
            )
        )
    return verdicts


def verify(claims: list[Claim], passages: list[Passage], verifier: Runnable) -> VerifyResult:
    if not claims:
        return VerifyResult([])
    cited_ids = {i for c in claims for i in c.citation_ids}
    cited = [p for p in passages if p.id in cited_ids]
    prompt = render(PROMPT, claims=format_claims(claims), passages=format_passages(cited))
    parsed, usage = invoke_structured(verifier, prompt, "Verifier")
    return VerifyResult(check_verdicts(parsed, claims, passages), usage)
