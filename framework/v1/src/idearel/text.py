"""Small text utilities shared by extractors and matchers."""
from __future__ import annotations

import re

DETERMINERS = {"a", "an", "the", "this", "that", "these", "those", "its", "their", "his", "her", "our", "my", "your"}
RELATIVE_PRONOUNS = {"that", "which", "who", "it", "they"}
STOPWORDS = DETERMINERS | {"of", "to", "in", "on", "for", "with", "and", "or", "by", "at", "from", "into", "is", "are",
                           "be", "can", "will", "as", "if", "when", "there", "so"}


def clean(text: str) -> str:
    text = (text or "").strip().strip(".;:,")
    return re.sub(r"\s+", " ", text)


def tokens(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)*", (text or "").lower())


def strip_determiners(phrase: str) -> str:
    toks = clean(phrase).split(" ")
    while toks and toks[0].lower() in DETERMINERS:
        toks = toks[1:]
    return " ".join(toks)


def content_words(phrase: str) -> list[str]:
    return [t for t in tokens(phrase) if t not in STOPWORDS]


def head_noun(phrase: str) -> str:
    """Last content word of a noun phrase ('heat-sensitive material' -> 'material')."""
    words = content_words(phrase)
    return words[-1] if words else ""


def split_free_text(text: str) -> tuple[str, str]:
    """Fallback segmentation of a free-text idea into WHAT and HOW.

    The paper collects WHAT/HOW/WHEN through a structured interface (or a GRU
    segmenter). Without them, we split at the first comma or at the first
    relative pronoun ('that', 'which'), which is how most ideas in the dataset
    are written ('Rescue Indication floor, that lights up ...').
    """
    t = clean(text)
    m = re.search(r",\s*|\s+(?=(that|which|who)\b)", t)
    if m:
        return t[:m.start()].strip(), t[m.end():].strip()
    return t, ""
