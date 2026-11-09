"""Dependency-based triple extraction with spaCy (offline default).

It reproduces the behaviour of OpenIE that matters for the rules:
    'Window composed of heat-sensitive material'      -> <window, composed of, heat-sensitive material>
    'The building consists of a variable structure'   -> <building, consists of, variable structure>
    'that lights up to show the exit path'            -> sequence of words (no explicit subject)
    'Window'                                          -> single term
"""
from __future__ import annotations

from ..models import Element, ElementType
from ..text import strip_determiners
from .base import Extractor, accept_subject, classify_without_triple

_NLP = None


def get_nlp(model: str = "en_core_web_md"):
    global _NLP
    if _NLP is None:
        import spacy
        try:
            _NLP = spacy.load(model)
        except OSError:
            _NLP = spacy.load("en_core_web_sm")
    return _NLP


def _phrase(tok) -> str:
    """Noun phrase headed by tok: compounds, adjectives and hyphenated modifiers, no determiners."""
    keep = [t for t in tok.subtree if t.dep_ not in ("det", "punct", "relcl", "acl", "prep", "cc", "conj", "advcl")
            or (t.dep_ == "punct" and t.text == "-")]
    # stop at the first clause/prep attached to the head
    left = [t for t in keep if t.i <= tok.i or t.head == tok and t.dep_ in ("compound", "amod")]
    words = sorted(set(left), key=lambda t: t.i)
    text = ""
    for t in words:
        text += t.text + ("" if t.text == "-" or (t.i + 1 < len(t.doc) and t.doc[t.i + 1].text == "-") else " ")
    return strip_determiners(text.strip())


class SpacyExtractor(Extractor):
    name = "spacy"

    def __init__(self, cfg: dict):
        super().__init__(cfg)
        self.nlp = get_nlp()

    def _extract(self, text: str, pattern_name: str, context: dict) -> Element:
        doc = self.nlp(text)
        verbs = [t for t in doc if t.pos_ in ("VERB", "AUX") and t.dep_ != "aux"]
        for v in verbs:
            subj = self._subject(v)
            pred, obj = self._predicate_object(v)
            if subj is None and pattern_name == "HOW" and v.i == 0:
                subj = ""                       # HOW written without subject: 'indicates the exit path'
            if subj is not None and obj is not None:
                s = accept_subject(subj, self.cfg, context)
                if s:
                    return Element(ElementType.TRIPLE, text=text, subject=s, predicate=pred, object=obj, source=self.name)
        return classify_without_triple(text, has_verb=bool(verbs), source=self.name)

    @staticmethod
    def _subject(v):
        for c in v.children:
            if c.dep_ in ("nsubj", "nsubjpass", "csubj"):
                return c.text if c.pos_ == "PRON" else _phrase(c)
        if v.dep_ in ("acl", "relcl") and v.head.pos_ in ("NOUN", "PROPN"):
            return _phrase(v.head)          # 'Window composed of ...': the modified noun is the subject
        return None

    @staticmethod
    def _predicate_object(v):
        pred = [v.lemma_ if v.dep_ not in ("acl",) else v.text]
        for c in v.children:
            if c.dep_ == "prt":
                pred.append(c.text)
        for c in v.children:
            if c.dep_ in ("dobj", "obj", "attr", "oprd"):
                return " ".join(pred), _phrase(c)
        for c in v.children:
            if c.dep_ in ("prep", "agent"):
                for g in c.children:
                    if g.dep_ == "pobj":
                        return " ".join(pred + [c.text]), _phrase(g)
        for c in v.children:
            if c.dep_ == "ccomp":               # 'indicates in which floor there are people' -> indicates floor
                for g in c.subtree:
                    if g.pos_ in ("NOUN", "PROPN") and g.dep_ in ("pobj", "nsubj", "dobj", "attr"):
                        return " ".join(pred), _phrase(g)
        for c in v.children:
            if c.dep_ in ("xcomp", "advcl"):    # "lights up to show the exit path" -> show path
                for g in c.children:
                    if g.dep_ in ("dobj", "obj"):
                        return " ".join(pred + [c.lemma_]), _phrase(g)
        return " ".join(pred), None
