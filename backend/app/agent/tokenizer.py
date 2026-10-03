"""Token counting and chunking via a HuggingFace tokenizer.

Used to budget context and to chunk documents for RAG / recall. The tokenizer
is loaded lazily and cached; set NAVEE_TOKENIZER_NAME (or tokenizer_name in
.env) to a local model dir for offline use.
"""

from functools import lru_cache

from app.core.config import settings


@lru_cache(maxsize=1)
def _tokenizer():
    from transformers import AutoTokenizer

    return AutoTokenizer.from_pretrained(settings.tokenizer_name)


def count_tokens(text: str) -> int:
    if not text:
        return 0
    return len(_tokenizer().encode(text))


def chunk_text(text: str, max_tokens: int) -> list[str]:
    """Split text into chunks of at most max_tokens each (whole-token aligned)."""
    if not text:
        return []
    if max_tokens <= 0:
        return [text]
    enc = _tokenizer()
    ids = enc.encode(text, add_special_tokens=False)
    slices = [ids[i : i + max_tokens] for i in range(0, len(ids), max_tokens)]
    return [enc.decode(chunk) for chunk in slices]


def truncate_to_tokens(text: str, max_tokens: int) -> str:
    """Whole-token-aligned prefix of text of at most max_tokens tokens."""
    if not text or max_tokens <= 0:
        return ""
    enc = _tokenizer()
    ids = enc.encode(text, add_special_tokens=False)
    return enc.decode(ids[:max_tokens])
