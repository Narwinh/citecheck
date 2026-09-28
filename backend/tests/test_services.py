import pytest
from google.genai import errors

from app.services.embeddings import CachedEmbedder, with_backoff
from app.services.search import CachedSearch
from tests.fakes import FakeTavily, bag_of_words_embed, page


def test_search_cache_hit_on_rerun(tmp_path):
    client = FakeTavily({"q": [page("https://a.com", "alpha text")]})
    search = CachedSearch(client, tmp_path)

    first = search.search("q")
    second = CachedSearch(client, tmp_path).search("q")  # fresh object, same disk cache

    assert client.calls == ["q"]
    assert first == second
    assert first[0].raw_content == "alpha text"


def test_search_cache_key_includes_params(tmp_path):
    client = FakeTavily({"q": []})
    CachedSearch(client, tmp_path, max_results=5).search("q")
    CachedSearch(client, tmp_path, max_results=3).search("q")
    assert client.calls == ["q", "q"]


def test_embedder_caches_and_preserves_order(tmp_path):
    calls: list[list[str]] = []

    def fn(texts, task):
        calls.append(texts)
        return bag_of_words_embed(texts, task)

    emb = CachedEmbedder(fn, tmp_path / "e.sqlite", "fake:64")
    first = emb.embed(["a b", "c d"], "RETRIEVAL_DOCUMENT")
    second = emb.embed(["c d", "e f", "a b"], "RETRIEVAL_DOCUMENT")

    assert calls == [["a b", "c d"], ["e f"]]
    assert second[0] == pytest.approx(first[1], abs=1e-6)
    assert second[2] == pytest.approx(first[0], abs=1e-6)
    assert (emb.hits, emb.misses) == (2, 3)


def test_embedder_cache_separates_task_types(tmp_path):
    calls = []
    emb = CachedEmbedder(
        lambda t, task: calls.append(task) or bag_of_words_embed(t, task),
        tmp_path / "e.sqlite",
        "fake:64",
    )
    emb.embed(["x"], "RETRIEVAL_DOCUMENT")
    emb.embed(["x"], "RETRIEVAL_QUERY")
    assert calls == ["RETRIEVAL_DOCUMENT", "RETRIEVAL_QUERY"]


def test_backoff_retries_429_then_succeeds():
    attempts, sleeps = [], []

    def flaky():
        attempts.append(1)
        if len(attempts) < 3:
            raise errors.ClientError(429, {"error": {"message": "rate limited"}})
        return "ok"

    assert with_backoff(flaky, sleep=sleeps.append) == "ok"
    assert sleeps == [2, 4]


def test_backoff_does_not_retry_bad_request():
    def bad():
        raise errors.ClientError(400, {"error": {"message": "bad"}})

    with pytest.raises(errors.ClientError):
        with_backoff(bad, sleep=lambda s: pytest.fail("should not sleep"))
