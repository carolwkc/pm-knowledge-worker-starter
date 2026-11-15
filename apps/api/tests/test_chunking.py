import pytest

from pmknowledge.chunking import chunk_text


def test_chunks_preserve_exact_unicode_offsets_and_paragraphs():
    text = "  αβ 👋\r\n\r\nTroubleshooting is slow.\n\nLast note.  "
    chunks = chunk_text(text, max_chars=30)
    assert [(c.text, c.start_char, c.end_char) for c in chunks] == [
        ("αβ 👋", 2, 6),
        ("Troubleshooting is slow.", 10, 34),
        ("Last note.", 36, 46),
    ]
    assert chunks == chunk_text(text, max_chars=30)
    assert all(text[c.start_char : c.end_char] == c.text for c in chunks)


def test_long_paragraph_splits_at_whitespace_without_dropping_words():
    text = "alpha beta gamma delta epsilon"
    chunks = chunk_text(text, max_chars=12)
    assert [c.text for c in chunks] == ["alpha beta", "gamma delta", "epsilon"]
    assert all(text[c.start_char : c.end_char] == c.text for c in chunks)


def test_long_unbroken_token_makes_progress_with_bounded_chunks():
    assert [c.text for c in chunk_text("abcdefghijk", max_chars=4)] == ["abcd", "efgh", "ijk"]


@pytest.mark.parametrize("text", ["", " \t\r\n"])
def test_empty_content_has_no_chunks(text):
    assert chunk_text(text) == []


def test_invalid_chunk_size_is_rejected():
    with pytest.raises(ValueError):
        chunk_text("text", max_chars=0)
