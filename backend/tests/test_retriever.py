from app.agents.retriever import RetrieverConfig, retrieve
from app.services.embeddings import CachedEmbedder
from app.services.search import CachedSearch
from tests.fakes import FakeTavily, bag_of_words_embed, page

CATS = "Cats are small domesticated felines. Cats purr and hunt mice."
DOGS = "Dogs are loyal domesticated canines. Dogs bark and fetch sticks."
RIVERS = "The Nile is a long river in Africa. The Nile flows north into the sea."


def make(tmp_path, pages):
    search = CachedSearch(FakeTavily(pages), tmp_path / "tavily")
    embedder = CachedEmbedder(bag_of_words_embed, tmp_path / "e.sqlite", "fake")
    return search, embedder


def test_passages_are_numbered_from_one_and_ranked(tmp_path):
    search, embedder = make(
        tmp_path, {"cats purr": [page("https://c.com", CATS), page("https://d.com", DOGS)]}
    )
    result = retrieve(["cats purr"], search, embedder)
    assert [p.id for p in result.passages] == list(range(1, len(result.passages) + 1))
    assert result.passages[0].url == "https://c.com"
    assert result.passages[0].score > result.passages[1].score


def test_round_robin_covers_every_sub_query(tmp_path):
    # Many cat pages would fill top_k=2 on raw score alone; the river hop must still appear.
    cat_pages = [page(f"https://cat{i}.com", f"{CATS} Variant {i}.") for i in range(5)]
    search, embedder = make(
        tmp_path,
        {"cats purr hunt mice": cat_pages, "nile river africa": [page("https://nile.org", RIVERS)]},
    )
    result = retrieve(
        ["cats purr hunt mice", "nile river africa"], search, embedder, RetrieverConfig(top_k=2)
    )
    assert {p.sub_query for p in result.passages} == {"cats purr hunt mice", "nile river africa"}


def test_same_url_from_two_sub_queries_is_chunked_once(tmp_path):
    shared = page("https://c.com", CATS)
    search, embedder = make(tmp_path, {"a cats": [shared], "b cats": [shared]})
    result = retrieve(["a cats", "b cats"], search, embedder)
    assert result.stats == {"pages": 1, "chunks": 1}
    assert len(result.passages) == 1


def test_near_duplicate_text_is_dropped(tmp_path):
    search, embedder = make(
        tmp_path,
        {"cats": [page("https://c.com", CATS), page("https://mirror.com", CATS)]},
    )
    result = retrieve(["cats"], search, embedder)
    assert len(result.passages) == 1


def test_no_results_gives_no_passages(tmp_path):
    search, embedder = make(tmp_path, {})
    assert retrieve(["nothing"], search, embedder).passages == []
