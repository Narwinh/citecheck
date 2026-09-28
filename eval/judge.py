"""LLM-as-judge: an independent label for each (claim, cited passages) pair.

Deliberately separate from the pipeline's verifier: a different prompt
(annotation guidelines, per-citation judgments, no evidence span) and a
different model generation, so the judge is not simply grading its own
homework. Its agreement with human labels is measured in metrics.py.
"""

from pathlib import Path
from string import Template

from langchain_core.runnables import Runnable
from pydantic import BaseModel

from app.agents.llm import format_passages, invoke_structured, structured
from app.state import Label, Passage

PROMPT_PATH = Path(__file__).parent / "prompts" / "judge_v1.md"
PROMPT_VERSION = "judge_v1"


class CitationJudgment(BaseModel):
    passage_id: int
    supports: bool


class ClaimJudgment(BaseModel):
    key: str
    label: Label
    citations: list[CitationJudgment]


class JudgeOutput(BaseModel):
    judgments: list[ClaimJudgment]


class JudgeItem(BaseModel):
    key: str  # "d3" = draft claim 3, "r3" = rewrite attempt for claim 3
    text: str
    citation_ids: list[int]


def structured_judge(llm) -> Runnable:
    return structured(llm, JudgeOutput)


def render_prompt(items: list[JudgeItem], passages: list[Passage]) -> str:
    lines = "\n".join(
        f"Item {i.key}: {i.text}\nCites: {', '.join(f'[{c}]' for c in i.citation_ids)}"
        for i in items
    )
    cited_ids = {c for i in items for c in i.citation_ids}
    cited = [p for p in passages if p.id in cited_ids]
    template = Template(PROMPT_PATH.read_text(encoding="utf-8"))
    return template.substitute(items=lines, passages=format_passages(cited))


def judge(
    items: list[JudgeItem], passages: list[Passage], judge_llm: Runnable
) -> tuple[dict[str, dict], dict[str, int]]:
    """Return ({key: {"label", "citations": {passage_id: bool}}}, usage).

    Items the judge skipped get label None so they are excluded from metrics
    rather than silently counted as supported or unsupported.
    """
    if not items:
        return {}, {}
    parsed, usage = invoke_structured(judge_llm, render_prompt(items, passages), "Judge")
    returned = {}
    for j in parsed.judgments:
        returned.setdefault(j.key, j)

    labels: dict[str, dict] = {}
    for item in items:
        j = returned.get(item.key)
        if j is None:
            labels[item.key] = {"label": None, "citations": {}}
            continue
        per_citation = {c.passage_id: c.supports for c in j.citations}
        labels[item.key] = {
            "label": j.label,
            "citations": {cid: per_citation.get(cid) for cid in item.citation_ids},
        }
    return labels, usage
