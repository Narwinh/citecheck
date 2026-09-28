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


def rejected_claims(claims: list[Claim], verdicts: list[Verdict], mode: Mode) -> list[Claim]:
    by_id = {v.claim_id: v for v in verdicts}
    return [c for c in claims if not passes(by_id[c.id].label, mode)]


@dataclass
class RecheckResult:
    revisions: list[Revision]  # sorted by claim id
    rewrites: dict[int, Claim]  # claim id -> rewrite that passed re-verification
    rewrite_verdicts: dict[int, Verdict]
    reviser_usage: dict[str, int]
    verifier_usage: dict[str, int]
    # Every rewrite with its re-verification verdict, passing or not. The eval uses
    # these to derive lenient-mode results from a strict run without new LLM calls.
    attempts: list[tuple[Claim, Verdict]] = field(default_factory=list)


def revise_and_recheck(
    question: str,
    rejected: list[Claim],
    verdicts: list[Verdict],
    passages: list[Passage],
    verifier: Runnable,
    reviser: Runnable,
    mode: Mode,
) -> RecheckResult:
    """One revision pass: rewrite or remove each rejected claim, then re-verify the rewrites."""
    by_id = {v.claim_id: v for v in verdicts}
    rewritten, revisions, reviser_usage = revise(question, rejected, by_id, passages, reviser)
    second = verify(rewritten, passages, verifier)

    rewrites: dict[int, Claim] = {}
    rewrite_verdicts: dict[int, Verdict] = {}
    for claim, verdict in zip(rewritten, second.verdicts, strict=True):
        if passes(verdict.label, mode):
            rewrites[claim.id] = claim
            rewrite_verdicts[claim.id] = verdict
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
    revisions.sort(key=lambda r: r.claim_id)
    attempts = list(zip(rewritten, second.verdicts, strict=True))
    return RecheckResult(
        revisions, rewrites, rewrite_verdicts, reviser_usage, second.usage, attempts
    )


def assemble_final(
    claims: list[Claim],
    verdicts: list[Verdict],
    revisions: list[Revision],
    rewrites: dict[int, Claim],
    rewrite_verdicts: dict[int, Verdict],
) -> tuple[list[Claim], list[Verdict]]:
    """Original order; rejected claims replaced by their passing rewrite or dropped."""
    removed = {r.claim_id for r in revisions if r.action == "removed"}
    by_id = {v.claim_id: v for v in verdicts} | rewrite_verdicts
    final = [rewrites.get(c.id, c) for c in claims if c.id not in removed]
    return final, [by_id[c.id] for c in final]


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
    rejected = rejected_claims(claims, first.verdicts, mode)
    if not rejected:
        return CheckResult(first.verdicts, [], list(claims), first.verdicts, usage)

    if allow_revision:
        recheck = revise_and_recheck(
            question, rejected, first.verdicts, passages, verifier, reviser, mode
        )
        usage["reviser"] = recheck.reviser_usage
        usage["verifier"] = add_usage(usage["verifier"], recheck.verifier_usage)
    else:
        removals = [Revision(claim_id=c.id, action="removed") for c in rejected]
        recheck = RecheckResult(removals, {}, {}, {}, {})

    final, final_verdicts = assemble_final(
        claims, first.verdicts, recheck.revisions, recheck.rewrites, recheck.rewrite_verdicts
    )
    return CheckResult(first.verdicts, recheck.revisions, final, final_verdicts, usage)
