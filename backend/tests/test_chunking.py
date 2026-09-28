import pytest

from app.services.chunking import chunk_text


def test_short_text_is_one_chunk():
    assert chunk_text("Hello world.  \n\n  Second para.") == ["Hello world. Second para."]


def test_empty_text_gives_no_chunks():
    assert chunk_text("   \n\n ") == []


def test_chunks_respect_size_and_overlap():
    sentences = [f"Sentence number {i} is here." for i in range(200)]
    text = " ".join(sentences)
    chunks = chunk_text(text, chunk_chars=300, overlap_chars=80)
    assert len(chunks) > 5
    assert all(len(c) <= 300 for c in chunks)
    # Each chunk after the first starts with text carried over from the previous one.
    for prev, nxt in zip(chunks, chunks[1:], strict=False):
        first_sentence = nxt.split(". ")[0]
        assert first_sentence in prev
    # Nothing is lost.
    for s in sentences:
        assert any(s in c for c in chunks)


def test_oversized_sentence_is_hard_split():
    chunks = chunk_text("x" * 1000, chunk_chars=300, overlap_chars=50)
    assert all(len(c) <= 300 for c in chunks)
    assert "".join(chunks).count("x") >= 1000


def test_overlap_must_be_smaller_than_chunk():
    with pytest.raises(ValueError):
        chunk_text("abc", chunk_chars=100, overlap_chars=100)
