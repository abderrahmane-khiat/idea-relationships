"""End-to-end pipeline: patterns -> elements -> links -> rules -> relationship with audit trail."""
from __future__ import annotations

import time

from .config import load_config
from .extraction import make_extractor
from .extraction.oracle import OracleExtractor
from .matching import make_cascade
from .models import Decision, Element, Idea
from .rules.engine import RuleEngine, what_head
from .text import split_free_text


class Framework:
    def __init__(self, cfg: dict | None = None, oracle: dict | str | None = None):
        self.cfg = cfg or load_config()
        try:
            base = make_extractor(self.cfg.get("extractor", "spacy"), self.cfg)
        except Exception as e:      # e.g. CoreNLP server not running, spaCy not installed
            base = make_extractor(self.cfg.get("extractor_fallback", "heuristic"), self.cfg)
            base.fallback_reason = f"{self.cfg.get('extractor')} unavailable ({type(e).__name__}: {e})"
        if oracle:
            self.extractor = (OracleExtractor.from_file(oracle, self.cfg, base) if isinstance(oracle, str)
                              else OracleExtractor(self.cfg, oracle, base))
        else:
            self.extractor = base
        self.cascade = make_cascade(self.cfg)
        if self.cfg.get("rules_version", "v1") == "v2":
            from .rules.v2 import RuleEngineV2
            self.engine = RuleEngineV2(self.cascade, self.cfg)
        else:
            self.engine = RuleEngine(self.cascade, self.cfg)
        self._elements: dict = {}
        self._fallback = None

    def elements(self, idea: Idea) -> tuple[Element, Element]:
        key = (idea.id, idea.text, idea.what, idea.how)
        if idea.id and key in self._elements:
            return self._elements[key]
        what, how = idea.what, idea.how
        if not what and idea.text:                      # free text only: Step 1 segmentation
            from .segmentation import segment
            seg = segment(idea.text, self.cfg.get("segmenter", "simple"), self.cfg)
            what, how = seg["what"], seg["how"]
        w = self._extract(what, "WHAT", {"idea_id": idea.id})
        h = self._extract(how, "HOW", {"idea_id": idea.id, "what_head": what_head(w)})
        if idea.id:
            self._elements[key] = (w, h)
        return w, h

    def _extract(self, text, pattern, ctx):
        """Extract; if the configured extractor fails (server down, model missing), use the fallback."""
        try:
            return self.extractor.extract(text, pattern, ctx)
        except Exception as e:
            if self._fallback is None:
                self._fallback = make_extractor(self.cfg.get("extractor_fallback", "heuristic"), self.cfg)
            self.extractor.fallback_reason = (f"{self.extractor.name} failed ({type(e).__name__}); "
                                              f"used {self._fallback.name} instead")
            return self._fallback.extract(text, pattern, ctx)

    def compare(self, idea1: Idea, idea2: Idea) -> Decision:
        t0 = time.perf_counter()
        w1, h1 = self.elements(idea1)
        w2, h2 = self.elements(idea2)
        d = self.engine.decide(idea1.id or "IDEA1", idea2.id or "IDEA2", w1, w2, h1, h2)
        d.notes.append(f"runtime {1000 * (time.perf_counter() - t0):.1f} ms; extractor {self.extractor.name}; "
                       f"cascade {' > '.join(self.cascade.order)}; rules {self.cfg.get('rules_version', 'v1')}")
        reason = getattr(self.extractor, "fallback_reason", "") or getattr(getattr(self.extractor, "fallback", None), "fallback_reason", "")
        if reason:
            d.notes.append(reason)
        return d
