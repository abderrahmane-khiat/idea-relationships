"""The four matching techniques. Each returns a MatcherCall; link == NO_LINK means 'not conclusive'."""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod

import numpy as np

from ..models import LinkType, MatcherCall
from ..text import STOPWORDS, content_words, tokens
from . import wordnet_utils as W


class Matcher(ABC):
    """pos: 'n' noun term, 'v' predicate, 's' sequence of words (free phrase)."""
    name = "matcher"
    applies_to = {"n", "v", "s"}

    def __init__(self, cfg: dict):
        self.cfg = cfg

    @abstractmethod
    def match(self, t1: str, t2: str, pos: str = "n") -> MatcherCall: ...

    def _none(self, t1, t2, score=None, thr=None, detail=""):
        return MatcherCall(self.name, t1, t2, score, thr, LinkType.NO_LINK, detail)


# ---------------------------------------------------------------- 1. structure-based
class StructureMatcher(Matcher):
    """Subclass/superclass/sameAs from a knowledge graph.

    backend = "sparql"   : local Wikidata/DBpedia endpoint (e.g. Blazegraph), as in the paper
    backend = "taxonomy" : local JSON file {"term": ["parent", ...]} (domain taxonomy)
    backend = "wordnet"  : offline alternative, WordNet noun hypernym hierarchy (default)
    """
    name = "structure"
    applies_to = {"n"}

    def __init__(self, cfg: dict):
        super().__init__(cfg)
        sc = cfg.get("structure", {})
        self.backend = sc.get("backend", "wordnet")
        self.depth = int(sc.get("max_hypernym_depth", 6))
        self.endpoint = sc.get("sparql_endpoint", "")
        self.try_modifiers = bool(sc.get("try_modifiers", True))
        self.taxonomy = {}
        if self.backend == "taxonomy" and sc.get("taxonomy_file"):
            with open(sc["taxonomy_file"], encoding="utf-8") as f:
                self.taxonomy = {k.lower(): [p.lower() for p in v] for k, v in json.load(f).items()}

    def match(self, t1, t2, pos="n"):
        if pos != "n":
            return self._none(t1, t2, detail="not applied to predicates")
        if self.backend == "sparql":
            return self._sparql(t1, t2)
        if self.backend == "taxonomy":
            return self._taxonomy(t1, t2)
        return self._wordnet(t1, t2)

    def _wordnet(self, t1, t2):
        s1, s2 = W.synsets(t1, "n"), W.synsets(t2, "n")
        if not s1 or not s2:
            return self._none(t1, t2, detail="term not found in WordNet")
        if set(s1) & set(s2):
            syn = sorted(set(s1) & set(s2), key=lambda s: s.name())[0]
            return MatcherCall(self.name, t1, t2, 1.0, None, LinkType.EQUALS, f"same concept {syn.name()}")
        for a in s1[:3]:
            for b in s2[:3]:
                up_a = {h: d for h, d in a.hypernym_distances() if 0 < d <= self.depth}
                if b in up_a:
                    return MatcherCall(self.name, t1, t2, 1.0, None, LinkType.SUBCLASS, f"{a.name()} is-a {b.name()} (depth {up_a[b]})")
                up_b = {h: d for h, d in b.hypernym_distances() if 0 < d <= self.depth}
                if a in up_b:
                    return MatcherCall(self.name, t1, t2, 1.0, None, LinkType.SUPERCLASS, f"{b.name()} is-a {a.name()} (depth {up_b[a]})")
        if self.try_modifiers:
            for x, y in ((t1, t2), (t2, t1)):
                words = content_words(y)
                for mod in words[:-1]:          # 'structure element': try 'structure'
                    r = self._hierarchy(W.synsets(x, "n"), tuple(W.wn().synsets(W.lemma(mod, "n"), "n")), t1, t2, x == t2)
                    if r:
                        r.detail += f" (via modifier '{mod}')"
                        return r
        return self._none(t1, t2, detail="no hierarchy link within depth")

    def _hierarchy(self, s1, s2, t1, t2, flipped):
        for a in s1[:3]:
            for b in s2[:3]:
                up_a = {h: d for h, d in a.hypernym_distances() if 0 < d <= self.depth}
                if b in up_a:
                    link = LinkType.SUPERCLASS if flipped else LinkType.SUBCLASS
                    return MatcherCall(self.name, t1, t2, 1.0, None, link, f"{a.name()} is-a {b.name()} (depth {up_a[b]})")
        return None

    def _taxonomy(self, t1, t2):
        a, b = t1.lower(), t2.lower()
        if a == b:
            return MatcherCall(self.name, t1, t2, 1.0, None, LinkType.EQUALS, "same term")
        if b in self._ancestors(a):
            return MatcherCall(self.name, t1, t2, 1.0, None, LinkType.SUBCLASS, "taxonomy")
        if a in self._ancestors(b):
            return MatcherCall(self.name, t1, t2, 1.0, None, LinkType.SUPERCLASS, "taxonomy")
        return self._none(t1, t2, detail="no taxonomy link")

    def _ancestors(self, t, seen=None):
        seen = seen or set()
        for p in self.taxonomy.get(t, []):
            if p not in seen:
                seen.add(p); self._ancestors(p, seen)
        return seen

    def _sparql(self, t1, t2):
        """Wikidata subclass-of (P279) path between the items labelled t1 and t2 on a LOCAL endpoint."""
        q = """SELECT ?dir WHERE {
          ?a rdfs:label "%s"@en . ?b rdfs:label "%s"@en .
          { ?a wdt:P279+ ?b . BIND("sub" AS ?dir) } UNION { ?b wdt:P279+ ?a . BIND("super" AS ?dir) }
          UNION { FILTER(?a = ?b) BIND("same" AS ?dir) } } LIMIT 1""" % (t1.replace('"', ''), t2.replace('"', ''))
        url = self.endpoint + "?" + urllib.parse.urlencode({"query": q, "format": "json"})
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"Accept": "application/sparql-results+json"}), timeout=20) as r:
                rows = json.loads(r.read().decode())["results"]["bindings"]
        except Exception as e:  # endpoint not running: not conclusive, cascade continues
            return self._none(t1, t2, detail=f"SPARQL endpoint unavailable ({type(e).__name__})")
        if not rows:
            return self._none(t1, t2, detail="no subclass path in KG")
        d = rows[0]["dir"]["value"]
        link = {"sub": LinkType.SUBCLASS, "super": LinkType.SUPERCLASS, "same": LinkType.EQUALS}[d]
        return MatcherCall(self.name, t1, t2, 1.0, None, link, "Wikidata P279")


# ---------------------------------------------------------------- 2. linguistic-based
_LEXICONS: dict = {}


def load_lexicon(path: str) -> dict:
    """Groups of words treated as synonyms; lemmatised once."""
    if not path:
        return {}
    if path not in _LEXICONS:
        from ..config import ROOT
        from pathlib import Path
        full = Path(path) if Path(path).is_absolute() else ROOT / path
        try:
            raw = json.loads(full.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raw = {}
        _LEXICONS[path] = {k: [{normalise(w, "v" if k == "verbs" else "n") for w in g} for g in raw.get(k, [])]
                           for k in ("verbs", "nouns")}
    return _LEXICONS[path]


def verb_head(predicate: str) -> str:
    """'is composed of' -> 'composed', 'lights up to show' -> 'lights'. Auxiliaries and particles are dropped."""
    aux = {"is", "are", "be", "been", "was", "were", "can", "could", "will", "would", "has", "have", "does", "do", "get", "gets"}
    words = [w for w in tokens(predicate) if w not in aux]
    words = [w for w in words if w not in STOPWORDS] or words
    return words[0] if words else predicate


def normalise(term: str, pos: str) -> str:
    if pos == "v":
        return W.lemma(verb_head(term), "v")
    words = content_words(term) or tokens(term)
    if not words:
        return ""
    words[-1] = W.lemma(words[-1], "n")
    return " ".join(words)
class LinguisticMatcher(Matcher):
    """Lin's information-theoretic similarity on WordNet (Lin, 1998); antonyms for predicates."""
    name = "linguistic"
    applies_to = {"n", "v"}

    def __init__(self, cfg: dict):
        super().__init__(cfg)
        self.thr = float(cfg["thresholds"]["linguistic"])
        lc = cfg.get("linguistic", {})
        self.ic = W.ic(lc.get("ic_corpus", "ic-brown.dat"))
        self.lexicon = load_lexicon(lc.get("lexicon_file", ""))

    def _lexicon(self, t1, t2, pos):
        groups = self.lexicon.get("verbs" if pos == "v" else "nouns", [])
        a, b = normalise(t1, pos), normalise(t2, pos)
        for g in groups:
            if a in g and b in g:
                return LinkType.EQUALS if a == b else LinkType.SYNONYM
        return None

    def match(self, t1, t2, pos="n"):
        lex = self._lexicon(t1, t2, pos)
        if lex:
            return MatcherCall(self.name, t1, t2, 1.0, self.thr, lex, "domain lexicon")
        if pos == "v":
            t1, t2 = verb_head(t1), verb_head(t2)
        s1, s2 = W.synsets(t1, pos), W.synsets(t2, pos)
        if not s1 or not s2:
            return self._none(t1, t2, thr=self.thr, detail="term not found in WordNet")
        if pos == "v":
            ants = {a.synset() for s in s1 for l in s.lemmas() for a in l.antonyms()}
            if ants & set(s2):
                return MatcherCall(self.name, t1, t2, 0.0, self.thr, LinkType.ANTONYM, "WordNet antonym")
        shared = set(s1) & set(s2)
        if shared:
            syn = sorted(shared, key=lambda x: x.name())[0]
            same = W.lemma(t1, pos) == W.lemma(t2, pos)
            return MatcherCall(self.name, t1, t2, 1.0, self.thr, LinkType.EQUALS if same else LinkType.SYNONYM,
                               f"shared WordNet sense {syn.name()}")
        best, pair = 0.0, None
        for a in s1[:5]:
            for b in s2[:5]:
                try:
                    v = a.lin_similarity(b, self.ic)
                except Exception:
                    continue
                if v and v > best:
                    best, pair = v, (a.name(), b.name())
        if best >= self.thr:
            link = LinkType.EQUALS if best >= 0.999 else LinkType.SYNONYM
            return MatcherCall(self.name, t1, t2, round(best, 4), self.thr, link, f"Lin({pair[0]}, {pair[1]})")
        return self._none(t1, t2, round(best, 4), self.thr, "below threshold")


# ---------------------------------------------------------------- 3. content-based
_VECTORS = None
_VECTORS_KEY = None


def load_vectors(cfg: dict):
    """Word vectors: a local word2vec/GloVe file, a gensim-data model, or spaCy vectors."""
    global _VECTORS
    c = cfg.get("content", {})
    key = (c.get("backend"), c.get("vectors"), c.get("vectors_file"))
    if _VECTORS is not None and _VECTORS_KEY == key:
        return _VECTORS
    globals()["_VECTORS_KEY"] = key
    if c.get("vectors_file"):
        from gensim.models import KeyedVectors
        path = c["vectors_file"]
        binary = path.endswith(".bin")
        _VECTORS = ("gensim", KeyedVectors.load_word2vec_format(path, binary=binary, no_header=path.endswith(".txt") and "glove" in path.lower()))
    elif c.get("backend", "gensim") == "gensim":
        import gensim.downloader as api
        _VECTORS = ("gensim", api.load(c.get("vectors", "glove-wiki-gigaword-100")))
    else:
        from ..extraction.spacy_extractor import get_nlp
        _VECTORS = ("spacy", get_nlp())
    return _VECTORS


class ContentMatcher(Matcher):
    """Distributional similarity (Word2Vec in the paper; any local word2vec/GloVe file here)."""
    name = "content"

    def __init__(self, cfg: dict):
        super().__init__(cfg)
        self.thr = float(cfg["thresholds"]["content"])
        self.kind, self.model = load_vectors(cfg)
        # "average": cosine of averaged vectors; "alignment": each word aligned to its most similar word in
        # the other phrase, averaged in both directions (Mihalcea et al., 2006). Applies to sequences of words.
        self.sentence_method = cfg.get("content", {}).get("sentence_method", "average")

    def word_vectors(self, phrase: str):
        out = []
        for w in content_words(phrase) or tokens(phrase):
            for cand in (w, w.replace("-", "")) + tuple(w.split("-")):
                if self.kind != "spacy" and cand in self.model.key_to_index:
                    out.append(self.model[cand]); break
        return out

    def alignment(self, t1, t2):
        a, b = self.word_vectors(t1), self.word_vectors(t2)
        if not a or not b:
            return None
        A = np.array(a) / np.linalg.norm(a, axis=1, keepdims=True)
        B = np.array(b) / np.linalg.norm(b, axis=1, keepdims=True)
        S = A @ B.T
        return float((S.max(axis=1).mean() + S.max(axis=0).mean()) / 2)

    def vector(self, phrase: str):
        words = content_words(phrase) or tokens(phrase)
        if self.kind == "spacy":
            v = self.model(" ".join(words)).vector
            return v if np.any(v) else None
        vecs = []
        for w in words:
            for cand in (w, w.replace("-", "")):
                if cand in self.model.key_to_index:
                    vecs.append(self.model[cand]); break
            else:
                for part in w.split("-"):
                    if part in self.model.key_to_index:
                        vecs.append(self.model[part])
        return np.mean(vecs, axis=0) if vecs else None

    def match(self, t1, t2, pos="n"):
        if pos == "s" and self.sentence_method == "alignment" and self.kind != "spacy":
            sim = self.alignment(t1, t2)
            if sim is None:
                return self._none(t1, t2, thr=self.thr, detail="no vector")
            if sim >= self.thr:
                return MatcherCall(self.name, t1, t2, round(sim, 4), self.thr, LinkType.SIMILAR, "word alignment similarity")
            return self._none(t1, t2, round(sim, 4), self.thr, "below threshold (word alignment)")
        a, b = self.vector(t1), self.vector(t2)
        if a is None or b is None:
            return self._none(t1, t2, thr=self.thr, detail="no vector")
        cos = float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
        if cos >= self.thr:
            return MatcherCall(self.name, t1, t2, round(cos, 4), self.thr, LinkType.SIMILAR, "cosine of averaged word vectors")
        return self._none(t1, t2, round(cos, 4), self.thr, "below threshold")


# ---------------------------------------------------------------- 4. terminology-based
def levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


class TerminologyMatcher(Matcher):
    """Normalised Levenshtein similarity (Levenshtein, 1966): 1 - distance / max length."""
    name = "terminology"

    def __init__(self, cfg: dict):
        super().__init__(cfg)
        self.thr = float(cfg["thresholds"]["terminology"])

    def match(self, t1, t2, pos="n"):
        a, b = " ".join(content_words(t1)) or t1.lower(), " ".join(content_words(t2)) or t2.lower()
        if not a or not b:
            return self._none(t1, t2, thr=self.thr)
        sim = 1 - levenshtein(a, b) / max(len(a), len(b))
        if sim >= self.thr:
            return MatcherCall(self.name, t1, t2, round(sim, 4), self.thr, LinkType.EQUALS, "string similarity")
        return self._none(t1, t2, round(sim, 4), self.thr, "below threshold")


MATCHERS = {"structure": StructureMatcher, "linguistic": LinguisticMatcher,
            "content": ContentMatcher, "terminology": TerminologyMatcher}
