"""Oracle mode (Reviewer 1, comment 7): elements are given by a human instead of being extracted.

Oracle file format (JSON):
{
  "IDEA020": {
    "WHAT": {"type": "single_term", "text": "rescue indication floor"},
    "HOW":  {"type": "triple", "subject": "floor", "predicate": "lights up to show", "object": "exit path"}
  },
  ...
}
Ideas or patterns missing from the file fall back to the normal extractor, so a
partial oracle (e.g. only corrected HOW triples) is possible.
"""
from __future__ import annotations

import json
from pathlib import Path

from ..models import Element
from .base import Extractor


class OracleExtractor(Extractor):
    name = "oracle"

    def __init__(self, cfg: dict, elements: dict | None = None, fallback: Extractor | None = None):
        super().__init__(cfg)
        self.elements = elements or {}
        self.fallback = fallback

    @staticmethod
    def from_file(path: str | Path, cfg: dict, fallback: Extractor | None = None) -> "OracleExtractor":
        with open(path, encoding="utf-8") as f:
            return OracleExtractor(cfg, json.load(f), fallback)

    def lookup(self, idea_id: str, pattern_name: str) -> Element | None:
        d = self.elements.get(idea_id, {}).get(pattern_name)
        if d:
            el = Element.from_dict(d)
            el.source = "oracle"
            return el
        return None

    def _extract(self, text: str, pattern_name: str, context: dict) -> Element:
        el = self.lookup(context.get("idea_id", ""), pattern_name)
        if el is not None:
            return el
        if self.fallback is None:
            raise KeyError(f"oracle has no {pattern_name} element for {context.get('idea_id')!r} and no fallback")
        return self.fallback.extract(text, pattern_name, context)
