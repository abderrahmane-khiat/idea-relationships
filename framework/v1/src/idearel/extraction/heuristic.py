"""Pure-Python fallback extractor using NLTK part-of-speech tags.

Used when spaCy is not installed. Pattern: <noun phrase> <verb (+particle/preposition)> <noun phrase>.
"""
from __future__ import annotations

from ..models import Element, ElementType
from ..text import clean, strip_determiners
from .base import Extractor, accept_subject, classify_without_triple

PREPS = {"of", "to", "in", "on", "into", "with", "from", "by", "for", "along", "through", "at", "over", "under", "up", "down", "out"}


def pos_tag(text: str) -> list[tuple[str, str]]:
    try:
        import nltk
        return nltk.pos_tag(nltk.word_tokenize(text))
    except Exception:  # no NLTK data: crude guess, every word ending in -s/-ed/-es after a noun is a verb
        out = []
        for i, w in enumerate(text.split()):
            out.append((w, "VBZ" if i > 0 and (w.endswith("s") or w.endswith("ed")) else "NN"))
        return out


class HeuristicExtractor(Extractor):
    name = "heuristic"

    def _extract(self, text: str, pattern_name: str, context: dict) -> Element:
        tagged = pos_tag(clean(text))
        is_np = lambda t: t.startswith(("NN", "JJ")) or t in ("CD", "HYPH")
        verbs = [i for i, (_, t) in enumerate(tagged) if t in ("VBZ", "VBP", "VBD", "VBN", "VB")]
        for vi in verbs:
            k = vi - 1
            while k >= 0 and (is_np(tagged[k][1]) or tagged[k][0] == "-"):
                k -= 1
            subj_words = [w for w, _ in tagged[k + 1:vi]]
            j, pred = vi + 1, [tagged[vi][0]]
            while j < len(tagged) and (tagged[j][0].lower() in PREPS or tagged[j][1] in ("RP", "IN", "TO", "RB")):
                pred.append(tagged[j][0]); j += 1
            if j < len(tagged) and tagged[j][1].startswith("VB"):        # 'to show the exit path'
                pred.append(tagged[j][0]); j += 1
            while j < len(tagged) and tagged[j][1] in ("DT", "PRP$"):
                j += 1
            obj_words = []
            while j < len(tagged) and (is_np(tagged[j][1]) or tagged[j][0] == "-"):
                obj_words.append(tagged[j][0]); j += 1
            s = accept_subject(" ".join(subj_words), self.cfg, context)
            obj = strip_determiners(" ".join(obj_words))
            if s and obj:
                return Element(ElementType.TRIPLE, text=text, subject=s, predicate=" ".join(pred), object=obj, source=self.name)
        return classify_without_triple(text, has_verb=bool(verbs), source=self.name)
