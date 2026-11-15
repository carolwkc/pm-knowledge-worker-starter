"""Deterministic, non-overlapping spans in the original Unicode text."""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    text: str
    start_char: int
    end_char: int


def chunk_text(text: str, max_chars: int = 1000) -> list[TextChunk]:
    if max_chars < 1:
        raise ValueError("max_chars must be positive")
    chunks = []
    for paragraph in re.finditer(r"\S.*?(?=\r?\n[ \t]*\r?\n|\Z)", text, re.DOTALL):
        start = paragraph.start()
        stop = paragraph.end()
        while start < stop:
            while start < stop and text[start].isspace():
                start += 1
            if start == stop:
                break
            end = min(start + max_chars, stop)
            if end < stop and not text[end].isspace():
                boundaries = list(re.finditer(r"\s+", text[start:end]))
                if boundaries:
                    end = start + boundaries[-1].start()
            while end > start and text[end - 1].isspace():
                end -= 1
            chunks.append(TextChunk(text[start:end], start, end))
            start = end
    return chunks
