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
import os
import random
import re
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


PREVIEW_SENTENCES = 3
STOPWORDS = {
    "a", "an", "the", "of", "in", "on", "at", "to", "for", "and", "or", "but", "is", "are",
    "was", "were", "be", "been", "by", "with", "as", "from", "that", "this", "it", "its",
    "into", "than", "then", "there", "their", "they", "which", "who", "what", "when",
    "where", "how", "some",
}  # fmt: skip
HIGHLIGHT, RESET = "\033[1;33m", "\033[0m"


def words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+(?:\.[0-9]+)?", text.lower()) if w not in STOPWORDS}


def highlight(text: str, claim_words: set[str]) -> str:
    return re.sub(
        r"[A-Za-z0-9]+(?:\.[0-9]+)?",
        lambda m: (
            f"{HIGHLIGHT}{m.group()}{RESET}" if m.group().lower() in claim_words else m.group()
        ),
        text,
    )


def preview(text: str, claim: str, k: int = PREVIEW_SENTENCES) -> list[str]:
    """The k sentences sharing the most words with the claim, in passage order.

    Pure word overlap, no model involved, so the preview can't hint at a label.
    It can miss the deciding sentence, which is why the full text is one key away.
    """
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", " ".join(text.split())) if s]
    target = words(claim)
    ranked = sorted(range(len(sentences)), key=lambda i: -len(words(sentences[i]) & target))
    return [sentences[i] for i in sorted(ranked[:k])]


def show(i: int, total: int, qid: str, question: str, claim: str, cited: list[dict], full: bool):
    claim_words = words(claim)
    print("=" * 78)
    print(f"[{i}/{total}] {qid}: {question}\n")
    print(textwrap.fill(f"CLAIM: {claim}", 78))
    for p in cited:
        print(f"\n[{p['id']}] {p['title']} ({p['url']})")
        if full:
            body = textwrap.fill(p["text"], 74)
            print(textwrap.indent(highlight(body, claim_words), "    "))
            continue
        for sentence in preview(p["text"], claim):
            wrapped = textwrap.fill(
                sentence, 72, initial_indent="  ... ", subsequent_indent="      "
            )
            print(highlight(wrapped, claim_words))
        n = len(re.split(r"(?<=[.!?])\s+", p["text"].strip()))
        print(f"      (closest {PREVIEW_SENTENCES} of {n} sentences; press f for the full source)")


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
    os.system("")  # turns on ANSI colour handling in the Windows console

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
        cited = [p for p in passages if p["id"] in item.citation_ids]
        show(i, len(todo), qid, record["question"], item.text, cited, full=False)
        while True:
            answer = input("\nLabel (s/p/u, f=full source, q=quit): ").strip().lower()
            if answer == "q":
                return 0
            if answer == "f":
                show(i, len(todo), qid, record["question"], item.text, cited, full=True)
                continue
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
