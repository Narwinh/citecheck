"""Reviser (the writer's second pass) and the verify -> revise -> re-verify flow.

One revision pass, maximum. Rewrites keep the original claim ID so the UI can
animate the same sentence changing. A rewrite that fails re-verification is
removed rather than revised again: a second loop would add another two LLM
calls of latency for claims that already failed twice.
"""

from dataclasses import dataclass, field
from typing import Any, Literal

from langchain_core.runnables import Runnable
from pydantic import BaseModel

from app.agents.llm import add_usage, format_passages, invoke_structured, structured
from app.agents.verifier import verify
from app.agents.writer import clean_text, valid_citations
from app.prompts import render
from app.state import Claim, Mode, Passage, Revision, Verdict, passes

PROMPT = "reviser_v1"


class RevisionOut(BaseModel):
    claim_id: int
    action: Literal["rewrite", "remove"]
    text: str | None = None
    citation_ids: list[int] = []


class ReviserOutput(BaseModel):
    decisions: list[RevisionOut]


def structured_reviser(llm: Any) -> Runnable:
    return structured(llm, ReviserOutput)


def format_rejected(claims: list[Claim], verdicts: dict[int, Verdict]) -> str:
    return "\n".join(
        f"Claim {c.id}: {c.text}\nCited: {c.citation_ids} · Verdict: "
        f"{verdicts[c.id].label} · Reason: {verdicts[c.id].rationale}"
        for c in claims
    )


def revise(
    question: str,
    rejected: list[Claim],
    verdicts: dict[int, Verdict],
    passages: list[Passage],
    reviser: Runnable,
) -> tuple[list[Claim], list[Revision], dict[str, int]]:
    """Return (rewritten claims, removals, usage). Unparseable decisions become removals."""
    prompt = render(
        PROMPT,
        question=question,
        claims=format_rejected(rejected, verdicts),
        passages=format_passages(passages),
    )
    parsed, usage = invoke_structured(reviser, prompt, "Reviser")
    decisions = {d.claim_id: d for d in reversed(parsed.decisions)}  # first one wins

    rewritten: list[Claim] = []
    removed: list[Revision] = []
    for claim in rejected:
        d = decisions.get(claim.id)
        text = clean_text(d.text or "") if d else ""
        cited = valid_citations(d.citation_ids, passages) if d else []
        if d and d.action == "rewrite" and text and cited:
            rewritten.append(Claim(id=claim.id, text=text, citation_ids=cited))
        else:
            removed.append(Revision(claim_id=claim.id, action="removed"))
    return rewritten, removed, usage


@dataclass
class CheckResult:
    draft_verdicts: list[Verdict]  # verifier's view of the writer's draft
    revisions: list[Revision]  # one per rejected claim: rewritten or removed
    final_claims: list[Claim]
    final_verdicts: list[Verdict]  # one per final claim
    usage: dict[str, dict[str, int]] = field(default_factory=dict)


def verify_and_revise(
    question: str,
    claims: list[Claim],
    passages: list[Passage],
    verifier: Runnable,
    reviser: Runnable,
    mode: Mode = "strict",
    allow_revision: bool = True,
) -> CheckResult:
    first = verify(claims, passages, verifier)
    usage = {"verifier": first.usage}
    verdicts = {v.claim_id: v for v in first.verdicts}
    rejected = [c for c in claims if not passes(verdicts[c.id].label, mode)]

    if not rejected:
        return CheckResult(first.verdicts, [], list(claims), first.verdicts, usage)

    revisions: list[Revision] = []
    kept_rewrites: dict[int, Claim] = {}
    if allow_revision:
        rewritten, removed, usage["reviser"] = revise(
            question, rejected, verdicts, passages, reviser
        )
        revisions.extend(removed)
        second = verify(rewritten, passages, verifier)
        usage["verifier"] = add_usage(usage["verifier"], second.usage)
        for claim, verdict in zip(rewritten, second.verdicts, strict=True):
            if passes(verdict.label, mode):
                kept_rewrites[claim.id] = claim
                verdicts[claim.id] = verdict
                revisions.append(
                    Revision(
                        claim_id=claim.id,
                        action="rewritten",
                        new_text=claim.text,
                        new_citation_ids=claim.citation_ids,
                    )
                )
            else:
                revisions.append(Revision(claim_id=claim.id, action="removed"))
    else:
        revisions = [Revision(claim_id=c.id, action="removed") for c in rejected]

    rejected_ids = {c.id for c in rejected}
    final_claims = [
        kept_rewrites.get(c.id, c)
        for c in claims
        if c.id not in rejected_ids or c.id in kept_rewrites
    ]
    revisions.sort(key=lambda r: r.claim_id)
    return CheckResult(
        first.verdicts,
        revisions,
        final_claims,
        [verdicts[c.id] for c in final_claims],
        usage,
    )
