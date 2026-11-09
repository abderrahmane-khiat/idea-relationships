"""Common extractor interface."""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import Element, ElementType
from ..text import clean, content_words, strip_determiners, RELATIVE_PRONOUNS

MAX_TERM_WORDS = 4


class Extractor(ABC):
    name = "base"

    def __init__(self, cfg: dict):
        self.cfg = cfg

    def extract(self, pattern: str, pattern_name: str = "WHAT", context: dict | None = None) -> Element:
        text = clean(pattern)
        if not text:
            return Element(ElementType.EMPTY, source=self.name)
        el = self._extract(text, pattern_name, context or {})
        el.source = el.source or self.name
        return el

    @abstractmethod
    def _extract(self, text: str, pattern_name: str, context: dict) -> Element: ...


def classify_without_triple(text: str, has_verb: bool, source: str) -> Element:
    """No triple: a short noun phrase is a single term, anything else a sequence of words."""
    phrase = strip_determiners(text)
    words = content_words(phrase)
    if words and not has_verb and len(phrase.split()) <= MAX_TERM_WORDS:
        return Element(ElementType.TERM, text=phrase, source=source)
    return Element(ElementType.SW, text=phrase, source=source)


def accept_subject(subject: str, cfg: dict, context: dict) -> str:
    """OpenIE does not produce a triple without an explicit subject.

    With implicit_how_subject=true, a relative pronoun ('that lights up ...')
    is replaced by the head of the idea's WHAT pattern, which mirrors how the
    experts validated HOW triples.
    """
    s = strip_determiners(subject)
    if s.lower() in RELATIVE_PRONOUNS or not s:
        if cfg.get("implicit_how_subject") and context.get("what_head"):
            return context["what_head"]
        return ""
    return s
