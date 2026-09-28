"""Per-request in-memory Chroma collection.

Every EphemeralClient in a process shares the same storage, so each request
gets a uniquely named collection that is dropped afterwards. Without that,
two concurrent API requests would see each other's passages.
"""

import uuid
from collections.abc import Iterator
from contextlib import contextmanager

import chromadb

_client = chromadb.EphemeralClient()


class RequestStore:
    def __init__(self, collection: chromadb.Collection):
        self.collection = collection

    def add(self, ids: list[str], embeddings: list[list[float]]) -> None:
        self.collection.add(ids=ids, embeddings=embeddings)

    def query(self, embedding: list[float], n: int) -> list[tuple[str, float]]:
        """Return (id, cosine similarity) pairs, best first."""
        n = min(n, self.collection.count())
        if n == 0:
            return []
        result = self.collection.query(
            query_embeddings=[embedding], n_results=n, include=["distances"]
        )
        return [(i, 1.0 - d) for i, d in zip(result["ids"][0], result["distances"][0], strict=True)]


@contextmanager
def request_store() -> Iterator[RequestStore]:
    name = f"req-{uuid.uuid4().hex}"
    collection = _client.create_collection(
        name, configuration={"hnsw": {"space": "cosine"}}, embedding_function=None
    )
    try:
        yield RequestStore(collection)
    finally:
        _client.delete_collection(name)
