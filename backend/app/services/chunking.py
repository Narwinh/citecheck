"""Split page text into overlapping chunks on paragraph and sentence boundaries.

Sizes are in characters. We approximate 1 token ~= 4 characters of English,
so the defaults (2400 chars, 400 overlap) land at roughly 600 tokens with
~100 tokens of overlap. That avoids adding a tokenizer dependency; the
embedding model's 2,048-token input limit leaves plenty of headroom.
"""

import re

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def _units(text: str, max_chars: int) -> list[str]:
    """Break text into pieces no longer than max_chars, preferring natural boundaries."""
    units: list[str] = []
    for para in re.split(r"\n\s*\n", text):
        para = " ".join(para.split())
        if not para:
            continue
        if len(para) <= max_chars:
            units.append(para)
            continue
        for sentence in _SENTENCE_END.split(para):
            while len(sentence) > max_chars:  # e.g. a table flattened into one line
                units.append(sentence[:max_chars])
                sentence = sentence[max_chars:]
            if sentence:
                units.append(sentence)
    return units


def chunk_text(text: str, chunk_chars: int = 2400, overlap_chars: int = 400) -> list[str]:
    if overlap_chars >= chunk_chars:
        raise ValueError("overlap_chars must be smaller than chunk_chars")

    chunks: list[str] = []
    current: list[str] = []
    for unit in _units(text, chunk_chars):
        if current and len(" ".join([*current, unit])) > chunk_chars:
            chunks.append(" ".join(current))
            # Carry trailing units forward as overlap, never the whole chunk.
            carried: list[str] = []
            for prev in reversed(current):
                if len(" ".join([prev, *carried])) > overlap_chars:
                    break
                carried.insert(0, prev)
            current = carried
            if current and len(" ".join([*current, unit])) > chunk_chars:
                current = []
        current.append(unit)
    if current:
        chunks.append(" ".join(current))
    return chunks
