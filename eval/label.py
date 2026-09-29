"""Hand-label a sample of claims, blind to the judge, for judge-vs-human agreement.

Usage (from the repo root):
    backend/.venv/Scripts/python eval/label.py --run-id dev30 --n 30

For each sampled claim you see the sentence and the full text of the passages it
cites, then type S (supported), P (partial) or U (unsupported). The judge's
label is never shown, so it can't anchor your answer. Answers are appended to
eval/human_labels.jsonl as you go; rerunning skips claims you already labelled.

Use the same definitions the judge uses (eval/prompts/judge_v1.md):
  S  everything the sentence asserts is in the cited passages
  P  the main point is there, but a detail is missing or it is overstated
  U  the main point is not there, or the passages contradict it
"""

import argparse
import json
import random
import sys
import textwrap
from datetime import UTC, datetime
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(EVAL_DIR.parent / "backend"))
sys.path.insert(0, str(EVAL_DIR))

from app.config import get_settings  # noqa: E402
from run_eval import judge_items, load_jsonl, load_results  # noqa: E402

KEYS = {"s": "SUPPORTED", "p": "PARTIAL", "u": "UNSUPPORTED"}


def pipeline_label(record: dict, key: str) -> str | None:
    """The verifier's label for a draft claim ("d3") or a rewrite ("r3")."""
    claim_id = int(key[1:])
    if key.startswith("d"):
        verdicts = record.get("verdicts", [])
        return next((v["label"] for v in verdicts if v["claim_id"] == claim_id), None)
    attempts = record.get("rewrite_attempts", [])
    return next((a["verdict"]["label"] for a in attempts if a["claim"]["id"] == claim_id), None)


def sample(records: dict[str, dict], n: int, seed: int) -> list[tuple[str, str]]:
    """(question_id, item_key) pairs, balanced across (judge label, verifier label) groups.

    Balancing on the judge alone fails when the judge gives nearly everything
    the same label; the claims where judge and verifier disagree are the
    informative ones, so every combination gets a fair share of the sample.
    """
    groups: dict[tuple, list[tuple[str, str]]] = {}
    for qid, r in sorted(records.items()):
        for key, j in (r.get("judge") or {}).items():
            if j.get("label"):
                groups.setdefault((j["label"], pipeline_label(r, key)), []).append((qid, key))
    rng = random.Random(seed)
    pools = [groups[g] for g in sorted(groups, key=str)]
    for pool in pools:
        rng.shuffle(pool)
    picked: list[tuple[str, str]] = []
    while len(picked) < n and any(pools):
        for pool in pools:
            if pool and len(picked) < n:
                picked.append(pool.pop())
    rng.shuffle(picked)  # don't present them grouped by label
    return picked


def main() -> int:
    parser = argparse.ArgumentParser(description="Blind hand-labelling of judged claims.")
    parser.add_argument("--run-id", default="dev30")
    parser.add_argument("--n", type=int, default=30)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--out", type=Path, default=EVAL_DIR / "human_labels.jsonl")
    args = parser.parse_args()

    records = load_results(EVAL_DIR / "results" / args.run_id / "results.jsonl")
    full_dir = get_settings().cache_dir / "runs" / args.run_id
    done = {(h["question_id"], h["key"]) for h in load_jsonl(args.out)}
    todo = [pair for pair in sample(records, args.n, args.seed) if pair not in done]
    print(f"{len(done)} already labelled, {len(todo)} to go. Type s / p / u, or q to stop.\n")

    for i, (qid, key) in enumerate(todo, 1):
        record = records[qid]
        item = next(it for it in judge_items(record) if it.key == key)
        cached = full_dir / f"{qid}.json"
        passages = json.loads(cached.read_text(encoding="utf-8")) if cached.is_file() else []
        print("=" * 78)
        print(f"[{i}/{len(todo)}] {qid}: {record['question']}\n")
        print(textwrap.fill(f"CLAIM: {item.text}", 78))
        for p in passages:
            if p["id"] in item.citation_ids:
                print(f"\n[{p['id']}] {p['title']} ({p['url']})")
                print(textwrap.indent(textwrap.fill(p["text"], 74), "    "))
        while True:
            answer = input("\nLabel (s/p/u, q=quit): ").strip().lower()
            if answer == "q":
                return 0
            if answer in KEYS:
                break
        with args.out.open("a", encoding="utf-8") as f:
            f.write(json.dumps({
                "question_id": qid,
                "key": key,
                "label": KEYS[answer],
                "run_id": args.run_id,
                "labeled_at": datetime.now(UTC).isoformat(timespec="seconds"),
            }) + "\n")  # fmt: skip
    print("\nAll sampled claims labelled. Re-summarize to see agreement:")
    print(
        f"  backend/.venv/Scripts/python eval/run_eval.py --run-id {args.run_id} --summarize-only"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
