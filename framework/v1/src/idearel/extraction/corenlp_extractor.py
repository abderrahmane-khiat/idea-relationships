"""Stanford CoreNLP OpenIE (Angeli et al., 2015), as used in the paper.

Start a local server first (Java 8+, CoreNLP 4.5.5):
    java -mx4g -cp "stanford-corenlp-4.5.5/*" edu.stanford.nlp.pipeline.StanfordCoreNLPServer -port 9000
No data leaves the machine.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request

from ..models import Element, ElementType
from .base import Extractor, accept_subject, classify_without_triple


class CoreNLPExtractor(Extractor):
    name = "corenlp"

    def __init__(self, cfg: dict):
        super().__init__(cfg)
        self.url = cfg.get("corenlp", {}).get("url", "http://localhost:9000")

    def _annotate(self, text: str) -> dict:
        props = {"annotators": "tokenize,ssplit,pos,lemma,depparse,natlog,openie", "outputFormat": "json",
                 "openie.triple.strict": "true"}
        q = urllib.parse.urlencode({"properties": json.dumps(props)})
        req = urllib.request.Request(f"{self.url}/?{q}", data=text.encode("utf-8"), method="POST")
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))

    def _extract(self, text: str, pattern_name: str, context: dict) -> Element:
        ann = self._annotate(text)
        triples, has_verb = [], False
        for sent in ann.get("sentences", []):
            has_verb |= any(t.get("pos", "").startswith("VB") for t in sent.get("tokens", []))
            triples += sent.get("openie", [])
        if triples:
            # the longest triple keeps the most information, like the paper's manual choice
            t = max(triples, key=lambda x: len(x["subject"]) + len(x["relation"]) + len(x["object"]))
            s = accept_subject(t["subject"], self.cfg, context)
            if s:
                return Element(ElementType.TRIPLE, text=text, subject=s, predicate=t["relation"], object=t["object"], source=self.name)
        return classify_without_triple(text, has_verb=has_verb, source=self.name)
