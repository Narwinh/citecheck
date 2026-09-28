"""Run the benchmark through the pipeline, judge every claim, and write a summary.

Usage (from the repo root, with the backend venv):
    backend/.venv/Scripts/python eval/run_eval.py --run-id dev30
    backend/.venv/Scripts/python eval/run_eval.py --run-id dev30 --limit 5
    backend/.venv/Scripts/python eval/run_eval.py --run-id dev30 --summarize-only

Built for the Gemini free tier (20 requests/day/model):
- Resumable. Each question's record is appended to results.jsonl as soon as it
  finishes; rerunning the same --run-id skips completed questions.
- Quota-aware. When every model reports its daily quota exhausted, the run
  stops cleanly and tells you to resume after midnight Pacific time. Per-minute
  limits wait and retry instead.
- One pipeline run (strict mode) per question feeds every ablation variant;
  see metrics.py.

Committed results keep passage URLs and short snippets only. Full passage text
(needed to re-judge) stays in the gitignored eval/cache/runs/.
"""

import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

EVAL_DIR = Path(__file__).resolve().parent
REPO_ROOT = EVAL_DIR.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))
sys.path.insert(0, str(EVAL_DIR))

from app.agents import planner, reviser, verifier, writer  # noqa: E402
from app.agents.llm import AllModelsFailed  # noqa: E402
from app.state import Passage  # noqa: E402
from judge import PROMPT_VERSION, JudgeItem, judge, structured_judge  # noqa: E402
from metrics import VARIANTS, summarize  # noqa: E402

SNIPPET_CHARS = 300
PER_MINUTE_WAIT_S = 65
MAX_RATE_RETRIES = 2


class QuotaExhausted(RuntimeError):
    pass


# ---------- files ----------


def load_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def load_results(path: Path) -> dict[str, dict]:
    """Latest record per question id wins, so reruns simply append."""
    return {r["id"]: r for r in load_jsonl(path)}


def append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


# ---------- records ----------


def _dump(obj: Any) -> Any:
    return obj.model_dump() if hasattr(obj, "model_dump") else obj


def record_from_state(item: dict, state: dict) -> dict:
    return {
        "id": item["id"],
        "question": item["question"],
        "category": item["category"],
        "status": "ok",
        "run_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "writer_status": state.get("writer_status"),
        "missing": state.get("missing"),
        "sub_queries": state.get("sub_queries", []),
        "passages": [
            {"id": p.id, "url": p.url, "title": p.title, "snippet": p.text[:SNIPPET_CHARS]}
            for p in state.get("passages", [])
        ],
        "draft_claims": [_dump(c) for c in state.get("draft_claims", [])],
        "verdicts": [_dump(v) for v in state.get("verdicts", [])],
        "rewrite_attempts": [
            {"claim": _dump(c), "verdict": _dump(v)} for c, v in state.get("rewrite_attempts", [])
        ],
        "revisions": [_dump(r) for r in state.get("revisions", [])],
        "final_claims": [_dump(c) for c in state.get("final_claims", [])],
        "timings_ms": state.get("timings_ms", {}),
        "token_usage": state.get("token_usage", {}),
        "total_ms": state.get("stats", {}).get("total_ms"),
    }


def judge_items(record: dict) -> list[JudgeItem]:
    items = [
        JudgeItem(key=f"d{c['id']}", text=c["text"], citation_ids=c["citation_ids"])
        for c in record["draft_claims"]
    ]
    for attempt in record["rewrite_attempts"]:
        c = attempt["claim"]
        items.append(JudgeItem(key=f"r{c['id']}", text=c["text"], citation_ids=c["citation_ids"]))
    return items


# ---------- running ----------


def _call_with_rate_retry(fn, *args, **kwargs):
    for attempt in range(MAX_RATE_RETRIES + 1):
        try:
            return fn(*args, **kwargs)
        except AllModelsFailed as exc:
            if exc.daily_quota_exhausted:
                raise QuotaExhausted(str(exc)) from exc
            per_minute = any("PerMinute" in str(e) for e in exc.errors)
            if not per_minute or attempt == MAX_RATE_RETRIES:
                raise
            print(f"    per-minute rate limit, waiting {PER_MINUTE_WAIT_S}s")
            time.sleep(PER_MINUTE_WAIT_S)
    raise AssertionError("unreachable")


def run_judge(record: dict, passages: list[Passage], judge_llm) -> dict:
    labels, usage = _call_with_rate_retry(judge, judge_items(record), passages, judge_llm)
    # JSON object keys must be strings, so passage ids are stored as "1", "2", ...
    record["judge"] = {
        key: {**j, "citations": {str(pid): ok for pid, ok in j["citations"].items()}}
        for key, j in labels.items()
    }
    record["judge_usage"] = usage
    record.pop("judge_error", None)
    return record


def evaluate_question(
    item: dict, graph, judge_llm, full_dir: Path, with_judge: bool
) -> tuple[dict, bool]:
    """Return (record, quota_hit). If only the judge ran out of quota, the pipeline
    record is still returned (unjudged) so it is saved and judged on resume."""
    from app.graph import run as run_graph

    state = _call_with_rate_retry(run_graph, graph, item["question"], mode="strict")
    record = record_from_state(item, state)
    full_dir.mkdir(parents=True, exist_ok=True)
    (full_dir / f"{item['id']}.json").write_text(
        json.dumps([p.model_dump() for p in state.get("passages", [])], ensure_ascii=False),
        encoding="utf-8",
    )
    if not with_judge:
        return record, False
    try:
        run_judge(record, state.get("passages", []), judge_llm)
    except QuotaExhausted:
        record["judge_error"] = "judge daily quota exhausted"
        return record, True
    except Exception as exc:  # noqa: BLE001 - keep the pipeline result, judge later
        record["judge_error"] = f"{type(exc).__name__}: {exc}"[:300]
    return record, False


def rejudge_pending(results: dict[str, dict], out: Path, full_dir: Path, judge_llm) -> None:
    for qid, record in results.items():
        if record.get("status") != "ok" or record.get("judge"):
            continue
        cached = full_dir / f"{qid}.json"
        if not cached.is_file():
            continue
        passages = [Passage(**p) for p in json.loads(cached.read_text(encoding="utf-8"))]
        print(f"  judging pending {qid}")
        try:
            append_jsonl(out, run_judge(record, passages, judge_llm))
        except QuotaExhausted:
            return


def run_benchmark(items, graph, judge_llm, out_dir: Path, full_dir: Path, with_judge=True):
    results_path = out_dir / "results.jsonl"
    results = load_results(results_path)
    if with_judge:
        rejudge_pending(results, results_path, full_dir, judge_llm)
        results = load_results(results_path)

    todo = [i for i in items if results.get(i["id"], {}).get("status") != "ok"]
    print(f"{len(items) - len(todo)} done, {len(todo)} to run")
    for n, item in enumerate(todo, 1):
        print(f"[{n}/{len(todo)}] {item['id']}: {item['question'][:70]}")
        start = time.perf_counter()
        quota_hit = False
        try:
            record, quota_hit = evaluate_question(item, graph, judge_llm, full_dir, with_judge)
        except QuotaExhausted:
            record, quota_hit = None, True
        except Exception as exc:  # noqa: BLE001 - record the failure and keep going
            record = {**item, "status": "error", "error": f"{type(exc).__name__}: {exc}"[:500]}
        if record is not None:
            append_jsonl(results_path, record)
            status = record["status"] + (" (unjudged)" if record.get("judge_error") else "")
            print(f"    {status} in {time.perf_counter() - start:.1f}s")
        if quota_hit:
            print("\nDaily quota exhausted for every model. Progress is saved.")
            print("Resume after midnight Pacific time with the same command.")
            return False
    return True


# ---------- summary ----------


def pct(x: float | None) -> str:
    return "n/a" if x is None else f"{x * 100:.1f}%"


def secs(ms: float | None) -> str:
    return "n/a" if ms is None else f"{ms / 1000:.1f}s"


def render_markdown(summary: dict, run_id: str) -> str:
    q = summary["questions"]
    lines = [
        f"# Eval summary: `{run_id}`",
        "",
        f"Questions: {q['completed']} completed of {q['total']} attempted, {q['judged']} judged. "
        f"By category: {q['by_category']}.",
        "",
        "## Claims by variant (independent judge)",
        "",
        "| Variant | Claims | Supported | Partial | Unsupported | Citation precision | Removed |",
        "|---|---|---|---|---|---|---|",
    ]
    for v in VARIANTS:
        m = summary["variants"][v]
        lines.append(
            f"| {v} | {m['claims']} | {pct(m['support_rate'])} | {pct(m['partial_rate'])} | "
            f"{pct(m['unsupported_rate'])} | {pct(m['citation_precision'])} | "
            f"{pct(m['removal_rate'])} |"
        )
    ab = summary["abstention"]
    lat = summary["latency"]
    tok = summary["tokens"]
    lines += [
        "",
        "## Abstention",
        "",
        "| Variant | Correct on unanswerable | False abstentions on answerable |",
        "|---|---|---|",
        *[
            f"| {v} | {pct(ab[v]['correct_abstentions'])} | {pct(ab[v]['false_abstentions'])} |"
            for v in ab
        ],
        "",
        "## Latency and cost",
        "",
        f"End to end: p50 {secs(lat['total_p50_ms'])}, p95 {secs(lat['total_p95_ms'])}.",
        "",
        "| Agent | p50 | p95 | n |",
        "|---|---|---|---|",
        *[
            f"| {a} | {secs(s['p50'])} | {secs(s['p95'])} | {s['n']} |"
            for a, s in lat["per_agent"].items()
        ],
        "",
        f"Mean tokens per question: {tok['mean_tokens_per_question']} "
        f"(by agent: {tok['mean_tokens_per_agent']}).",
        f"Model calls: {tok['model_calls']}.",
        "",
        "## Agreement",
        "",
        f"- Verifier vs judge on draft claims: {summary['verifier_vs_judge']}",
        f"- Judge vs human labels: {summary['judge_vs_human']}",
    ]
    return "\n".join(lines) + "\n"


def git_commit() -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=REPO_ROOT
        )
        return out.stdout.strip() or None
    except OSError:
        return None


def write_outputs(out_dir: Path, run_id: str, benchmark_path: Path, settings, human_path: Path):
    records = list(load_results(out_dir / "results.jsonl").values())
    summary = summarize(records, load_jsonl(human_path))
    config = {
        "run_id": run_id,
        "written_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "git_commit": git_commit(),
        "benchmark": str(benchmark_path.relative_to(REPO_ROOT)),
        "benchmark_sha256": hashlib.sha256(benchmark_path.read_bytes()).hexdigest()[:16],
        "pipeline_mode": "strict",
        "models": {
            "primary": settings.gemini_model,
            "fallbacks": settings.gemini_fallback_models,
            "judge": settings.judge_models,
            "embedding": f"{settings.gemini_embedding_model}:{settings.embedding_dimensions}",
        },
        "thinking": {
            "planner": settings.planner_thinking_level,
            "writer": settings.writer_thinking_level,
            "verifier": settings.verifier_thinking_level,
            "reviser": settings.reviser_thinking_level,
        },
        "prompts": {
            "planner": planner.PROMPT,
            "writer": writer.PROMPT,
            "verifier": verifier.PROMPT,
            "reviser": reviser.PROMPT,
            "judge": PROMPT_VERSION,
        },
        "retrieval": {"tavily_max_results": settings.tavily_max_results},
    }
    (out_dir / "config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (out_dir / "summary.md").write_text(render_markdown(summary, run_id), encoding="utf-8")
    return summary


def main() -> int:
    from app.config import get_settings
    from app.graph import build_graph
    from app.services.factory import make_agents, make_judge_llm

    parser = argparse.ArgumentParser(description="Run the CiteCheck benchmark.")
    parser.add_argument("--benchmark", type=Path, default=EVAL_DIR / "benchmark.jsonl")
    parser.add_argument("--run-id", default="dev")
    parser.add_argument("--limit", type=int, help="run at most N not-yet-done questions")
    parser.add_argument("--ids", help="comma-separated question ids to run")
    parser.add_argument("--no-judge", action="store_true")
    parser.add_argument("--summarize-only", action="store_true")
    parser.add_argument("--human-labels", type=Path, default=EVAL_DIR / "human_labels.jsonl")
    args = parser.parse_args()

    settings = get_settings()
    out_dir = EVAL_DIR / "results" / args.run_id
    full_dir = settings.cache_dir / "runs" / args.run_id
    items = load_jsonl(args.benchmark)
    if args.ids:
        wanted = set(args.ids.split(","))
        items = [i for i in items if i["id"] in wanted]

    if not args.summarize_only:
        if missing := settings.missing_keys():
            print(f"Missing {', '.join(missing)} in .env")
            return 1
        done = load_results(out_dir / "results.jsonl")
        if args.limit:
            pending = [i for i in items if done.get(i["id"], {}).get("status") != "ok"]
            keep = {i["id"] for i in pending[: args.limit]}
            items = [i for i in items if i["id"] in keep or i["id"] in done]
        graph = build_graph(make_agents(settings))
        judge_llm = structured_judge(make_judge_llm(settings))
        run_benchmark(items, graph, judge_llm, out_dir, full_dir, with_judge=not args.no_judge)

    summary = write_outputs(out_dir, args.run_id, args.benchmark, settings, args.human_labels)
    print(f"\nWrote {out_dir.relative_to(REPO_ROOT)}/summary.md")
    print(render_markdown(summary, args.run_id))
    return 0


if __name__ == "__main__":
    sys.exit(main())
