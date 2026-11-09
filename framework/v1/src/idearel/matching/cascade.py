"""Cascade of matchers (Section 4.3.3). Order and enabled matchers are configurable for ablation."""
from __future__ import annotations

from collections import Counter

from ..models import Link, LinkType
from ..text import clean
from .matchers import MATCHERS


class Cascade:
    def __init__(self, cfg: dict):
        c = cfg.get("cascade", {})
        order = c.get("order", list(MATCHERS))
        enabled = set(c.get("enabled", order))
        self.order = [m for m in order if m in enabled]
        self.matchers = [MATCHERS[m](cfg) for m in self.order]
        self._cache: dict = {}
        self.use_cache = bool(c.get("cache", True))
        self.stats = Counter()          # requests, cache_hits, calls_<matcher>

    def link(self, t1: str, t2: str, pos: str = "n") -> Link:
        """Run the matchers in order; stop at the first conclusive one (the audit trail keeps every call)."""
        t1, t2 = clean(t1), clean(t2)
        key = (t1.lower(), t2.lower(), pos)
        self.stats["requests"] += 1
        if self.use_cache and key in self._cache:
            self.stats["cache_hits"] += 1
            return self._cache[key]
        calls = []
        result = Link(t1, t2, LinkType.NO_LINK, "", calls)
        if t1 and t2:
            for m in self.matchers:
                if pos not in m.applies_to:
                    continue
                call = m.match(t1, t2, pos)
                self.stats[f"calls_{m.name}"] += 1
                calls.append(call)
                if call.link != LinkType.NO_LINK:
                    result = Link(t1, t2, call.link, m.name, calls)
                    break
        if self.use_cache:
            self._cache[key] = result
        return result


def make_cascade(cfg: dict) -> Cascade:
    return Cascade(cfg)
