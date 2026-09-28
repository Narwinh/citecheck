"""Gemini embeddings with batching, 429 backoff, and a SQLite disk cache.

Vectors are cached by (model, task type, dimensions, text), so rerunning the
eval re-embeds nothing. gemini-embedding-001 only returns unit-length vectors
at its full 3072 dims, so smaller outputs are normalized here.
"""

import hashlib
import math
import sqlite3
import time
from array import array
from collections.abc import Callable
from pathlib import Path
from typing import Literal, TypeVar

import httpx
from google import genai
from google.genai import errors, types

T = TypeVar("T")
TaskType = Literal["RETRIEVAL_DOCUMENT", "RETRIEVAL_QUERY"]
EmbedFn = Callable[[list[str], TaskType], list[list[float]]]

# Small batches spread a question's ~50-80 chunks over several requests, so a
# per-minute token limit on the free tier isn't hit in a single burst.
BATCH_SIZE = 25
MAX_RETRIES = 5


def normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vec))
    return [x / norm for x in vec] if norm else vec


def is_retryable(exc: Exception) -> bool:
    return isinstance(exc, errors.ServerError | httpx.TimeoutException) or (
        isinstance(exc, errors.ClientError) and exc.code == 429
    )


def with_backoff(call: Callable[[], T], sleep: Callable[[float], None] = time.sleep) -> T:
    for attempt in range(MAX_RETRIES):
        try:
            return call()
        except Exception as exc:
            if not is_retryable(exc) or attempt == MAX_RETRIES - 1:
                raise
            # 5, 10, 20, 40 s: 75 s in total, enough to outlast a one-minute quota window.
            sleep(5 * 2**attempt)
    raise AssertionError("unreachable")


class CachedEmbedder:
    def __init__(self, embed_fn: EmbedFn, cache_path: Path, cache_namespace: str):
        self.embed_fn = embed_fn
        self.namespace = cache_namespace
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(cache_path, check_same_thread=False)
        self.db.execute("CREATE TABLE IF NOT EXISTS vectors (key TEXT PRIMARY KEY, vec BLOB)")
        self.hits = 0
        self.misses = 0

    def _key(self, text: str, task: TaskType) -> str:
        return hashlib.sha256(f"{self.namespace}|{task}|{text}".encode()).hexdigest()

    def embed(self, texts: list[str], task: TaskType) -> list[list[float]]:
        keys = [self._key(t, task) for t in texts]
        found: dict[str, list[float]] = {}
        for i in range(0, len(keys), 500):  # stay under SQLite's variable limit
            batch = keys[i : i + 500]
            rows = self.db.execute(
                f"SELECT key, vec FROM vectors WHERE key IN ({','.join('?' * len(batch))})",
                batch,
            )
            found.update({k: array("f", v).tolist() for k, v in rows})

        todo = [(k, t) for k, t in dict(zip(keys, texts, strict=True)).items() if k not in found]
        self.hits += len(texts) - len(todo)
        self.misses += len(todo)
        for i in range(0, len(todo), BATCH_SIZE):
            batch = todo[i : i + BATCH_SIZE]
            vectors = self.embed_fn([t for _, t in batch], task)
            for (key, _), vec in zip(batch, vectors, strict=True):
                found[key] = normalize(vec)
            self.db.executemany(
                "INSERT OR REPLACE INTO vectors VALUES (?, ?)",
                [(k, array("f", found[k]).tobytes()) for k, _ in batch],
            )
            self.db.commit()
        return [found[k] for k in keys]


def gemini_embed_fn(api_key: str, model: str, dimensions: int) -> EmbedFn:
    # 60 s timeout (the SDK default is none, so a stalled request hangs forever);
    # retries are left to with_backoff so they aren't doubled up inside the SDK.
    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            timeout=60_000, retry_options=types.HttpRetryOptions(attempts=1)
        ),
    )

    def embed(texts: list[str], task: TaskType) -> list[list[float]]:
        result = with_backoff(
            lambda: client.models.embed_content(
                model=model,
                contents=texts,
                config=types.EmbedContentConfig(task_type=task, output_dimensionality=dimensions),
            )
        )
        return [list(e.values) for e in result.embeddings]

    return embed
