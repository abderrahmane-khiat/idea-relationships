"""WordNet helpers (NLTK). Multi-word terms are looked up as a whole ('fire_door'), then by their head."""
from __future__ import annotations

from functools import lru_cache

from ..text import content_words, head_noun

_WN = None
_IC = None


def wn():
    global _WN
    if _WN is None:
        from nltk.corpus import wordnet
        wordnet.ensure_loaded()
        _WN = wordnet
    return _WN


def ic(name: str = "ic-brown.dat"):
    global _IC
    if _IC is None:
        from nltk.corpus import wordnet_ic
        _IC = wordnet_ic.ic(name)
    return _IC


def lemma(word: str, pos: str) -> str:
    w = wn()
    base = w.morphy(word.lower().replace(" ", "_"), {"n": w.NOUN, "v": w.VERB}.get(pos, w.NOUN))
    return base or word.lower().replace(" ", "_")


@lru_cache(maxsize=20000)
def synsets(term: str, pos: str = "n") -> tuple:
    """Synsets of the whole term; if none, of its head word (nouns) or first content word (verbs)."""
    w = wn()
    p = w.NOUN if pos == "n" else w.VERB
    words = content_words(term)
    if not words:
        return ()
    whole = "_".join(words)
    found = w.synsets(whole, pos=p) or w.synsets(lemma(whole, pos), pos=p)
    if found:
        return tuple(found)
    key = head_noun(term) if pos == "n" else words[0]
    return tuple(w.synsets(lemma(key, pos), pos=p))
