"""Metrics over per-question result records (see run_eval.py for the record shape).

One pipeline run in strict mode yields every ablation variant:
- off:            the writer's draft, as if no verifier existed
- remove_strict:  verifier on, rejected claims (PARTIAL/UNSUPPORTED) removed, no revision
- remove_lenient: verifier on, only UNSUPPORTED removed, no revision
- revise_strict:  the full pipeline (what the user sees by default)
- revise_lenient: PARTIAL kept; UNSUPPORTED replaced by its rewrite if that rewrite
                  re-verified as SUPPORTED or PARTIAL, else removed

Caveat for revise_lenient: in the strict run the reviser also saw PARTIAL claims
in the same batch, so its rewrites of UNSUPPORTED claims may differ slightly from
a true lenient run. Every claim in every variant is judged by the same
independent judge, so variants are compared on equal terms.
"""

import math
from collections import Counter
from typing import Any

VARIANTS = ["off", "remove_strict", "remove_lenient", "revise_strict", "revise_lenient"]
LABELS = ["SUPPORTED", "PARTIAL", "UNSUPPORTED"]


def _passes(label: str | None, lenient: bool) -> bool:
    return label == "SUPPORTED" or (lenient and label == "PARTIAL")


def variant_keys(record: dict[str, Any], variant: str) -> list[str]:
    """Judge-item keys ("d3" draft claim 3, "r3" rewrite of claim 3) for one variant."""
    drafts = record.get("draft_claims", [])
    if variant == "off":
        return [f"d{c['id']}" for c in drafts]

    verdicts = {v["claim_id"]: v["label"] for v in record.get("verdicts", [])}
    rewrites = {a["claim"]["id"]: a["verdict"]["label"] for a in record.get("rewrite_attempts", [])}
    lenient = variant.endswith("lenient")
    keys = []
    for c in drafts:
        cid = c["id"]
        if _passes(verdicts.get(cid), lenient):
            keys.append(f"d{cid}")
        elif variant.startswith("revise") and _passes(rewrites.get(cid), lenient):
            keys.append(f"r{cid}")
    return keys


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    s = sorted(values)
    pos = (len(s) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def _rate(n: int, d: int) -> float | None:
    return round(n / d, 4) if d else None


def claim_metrics(records: list[dict], variant: str) -> dict[str, Any]:
    labels: Counter = Counter()
    cites_ok = cites_total = n_claims = n_draft = unjudged = 0
    for r in records:
        keys = variant_keys(r, variant)
        n_claims += len(keys)
        n_draft += len(r.get("draft_claims", []))
        for k in keys:
            j = r.get("judge", {}).get(k)
            if not j or j.get("label") is None:
                unjudged += 1
                continue
            labels[j["label"]] += 1
            for ok in j.get("citations", {}).values():
                if ok is not None:
                    cites_total += 1
                    cites_ok += bool(ok)
    judged = sum(labels.values())
    return {
        "claims": n_claims,
        "judged": judged,
        "unjudged": unjudged,
        "support_rate": _rate(labels["SUPPORTED"], judged),
        "partial_rate": _rate(labels["PARTIAL"], judged),
        "unsupported_rate": _rate(labels["UNSUPPORTED"], judged),
        "citation_precision": _rate(cites_ok, cites_total),
        "removal_rate": _rate(n_draft - n_claims, n_draft) if variant != "off" else 0.0,
    }


def abstention_metrics(records: list[dict]) -> dict[str, Any]:
    def abstained(r: dict, variant: str) -> bool:
        return r.get("writer_status") == "unanswerable" or not variant_keys(r, variant)

    out = {}
    unanswerable = [r for r in records if r["category"] == "unanswerable"]
    answerable = [r for r in records if r["category"] != "unanswerable"]
    for variant in ["off", "revise_strict"]:
        out[variant] = {
            "unanswerable_questions": len(unanswerable),
            "correct_abstentions": _rate(
                sum(abstained(r, variant) for r in unanswerable), len(unanswerable)
            ),
            "false_abstentions": _rate(
                sum(abstained(r, variant) for r in answerable), len(answerable)
            ),
        }
    return out


def latency_metrics(records: list[dict]) -> dict[str, Any]:
    totals = [r["total_ms"] for r in records if r.get("total_ms") is not None]
    agents = sorted({a for r in records for a in r.get("timings_ms", {})})
    per_agent = {}
    for a in agents:
        vals = [r["timings_ms"][a] for r in records if a in r.get("timings_ms", {})]
        per_agent[a] = {"p50": percentile(vals, 0.5), "p95": percentile(vals, 0.95), "n": len(vals)}
    return {
        "total_p50_ms": percentile(totals, 0.5),
        "total_p95_ms": percentile(totals, 0.95),
        "per_agent": per_agent,
        "samples": totals,
    }


def token_metrics(records: list[dict]) -> dict[str, Any]:
    per_q = []
    per_agent: Counter = Counter()
    models: Counter = Counter()
    for r in records:
        usage = r.get("token_usage", {})
        per_q.append(sum(u.get("total_tokens", 0) for u in usage.values()))
        for agent, u in usage.items():
            per_agent[agent] += u.get("total_tokens", 0)
            for k, n in u.items():
                if k.startswith("calls:"):
                    models[k.removeprefix("calls:")] += n
    n = len(per_q)
    return {
        "mean_tokens_per_question": round(sum(per_q) / n) if n else None,
        "mean_tokens_per_agent": {a: round(t / n) for a, t in per_agent.items()} if n else {},
        "model_calls": dict(models),
    }


def cohens_kappa(pairs: list[tuple[str, str]]) -> float | None:
    if not pairs:
        return None
    n = len(pairs)
    observed = sum(a == b for a, b in pairs) / n
    left, right = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    expected = sum(left[k] * right[k] for k in LABELS) / (n * n)
    return round((observed - expected) / (1 - expected), 4) if expected < 1 else 1.0


def agreement(pairs: list[tuple[str, str]]) -> dict[str, Any]:
    """Exact 3-way agreement, kappa, and agreement on the strict pass/fail decision."""
    if not pairs:
        return {"n": 0}
    return {
        "n": len(pairs),
        "exact": round(sum(a == b for a, b in pairs) / len(pairs), 4),
        "kappa": cohens_kappa(pairs),
        "pass_fail": round(
            sum((a == "SUPPORTED") == (b == "SUPPORTED") for a, b in pairs) / len(pairs), 4
        ),
    }


def verifier_vs_judge(records: list[dict]) -> dict[str, Any]:
    pairs = []
    for r in records:
        for v in r.get("verdicts", []):
            j = r.get("judge", {}).get(f"d{v['claim_id']}")
            if j and j.get("label"):
                pairs.append((v["label"], j["label"]))
    return agreement(pairs)


def judge_vs_human(records: list[dict], human: list[dict]) -> dict[str, Any]:
    by_q = {r["id"]: r for r in records}
    pairs = []
    for h in human:
        r = by_q.get(h["question_id"])
        j = (r or {}).get("judge", {}).get(h["key"])
        if j and j.get("label") and h.get("label") in LABELS:
            pairs.append((h["label"], j["label"]))
    return agreement(pairs)


def summarize(records: list[dict], human: list[dict] | None = None) -> dict[str, Any]:
    ok = [r for r in records if r.get("status") == "ok"]
    judged = [r for r in ok if r.get("judge")]
    return {
        "questions": {
            "total": len(records),
            "completed": len(ok),
            "judged": len(judged),
            "by_category": dict(Counter(r["category"] for r in ok)),
        },
        "variants": {v: claim_metrics(judged, v) for v in VARIANTS},
        "abstention": abstention_metrics(ok),
        "latency": latency_metrics(ok),
        "tokens": token_metrics(ok),
        "verifier_vs_judge": verifier_vs_judge(judged),
        "judge_vs_human": judge_vs_human(judged, human or []),
    }
