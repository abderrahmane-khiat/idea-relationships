"""Rules version 2 (future work; NOT the rule set of the paper).

Version 1 (catalog.py / engine.py) implements the 54 rules of Appendix B as published. Version 2 keeps the
same ideas and the same matchers but decides with ONE table, derived from the definitions of the five
relationship types, instead of 41 case-specific WHAT rules:

  Step A  WHAT evidence  ->  SAME | HIER | RELATED | NONE       (whatever the element types are)
  Step B  HOW evidence   ->  SAME | PARTIAL | DIFFERENT         (three levels instead of two)
  Step C  evidence check ->  UNKNOWN when a pattern is missing or the deciding link is weak
  Step D  decision table (R01-R12)

Decision table (rows: WHAT, columns: HOW)
                 SAME                 PARTIAL                 DIFFERENT
    SAME         R01 duplicate        R02 similar             R03 similar
    HIER         R04 generalise/det.  R05 similar             R06 disjoint (*)
    RELATED      R07 similar          R08 similar             R09 disjoint
    NONE         R10 alternative      R11 alternative         R12 disjoint

(*) rules_v2.hier_different = "disjoint" (default) | "similar". Two artefacts of the same broad class that
    do different things share no functional evidence; set to "similar" to count the taxonomic link alone.

Unknown (abstain) rules
    U01  WHAT missing or empty for at least one idea
    U02  HOW missing or empty for at least one idea (the HOW decides 9 of the 12 cells)
    U03  the cell is decided by a weak link: a link found only through a modifier word, a link between
         generic heads (system, device, structure, ...), or a score within `rules_v2.margin` of the threshold
    U04  the two patterns could not be compared (no vector, no WordNet entry) for the deciding element
"""
from __future__ import annotations

from ..matching.cascade import Cascade
from ..models import Decision, Element, ElementType as T, Link, LinkType, Relationship as R
from ..text import content_words, head_noun

SAME, HIER, RELATED, NONE = "SAME", "HIER", "RELATED", "NONE"
H_SAME, H_PARTIAL, H_DIFF = "SAME", "PARTIAL", "DIFFERENT"

TABLE = {
    (SAME, H_SAME): ("R01", R.DUPLICATE), (SAME, H_PARTIAL): ("R02", R.SIMILAR), (SAME, H_DIFF): ("R03", R.SIMILAR),
    (HIER, H_SAME): ("R04", R.GENERALISE_DETAIL), (HIER, H_PARTIAL): ("R05", R.SIMILAR), (HIER, H_DIFF): ("R06", R.DISJOINT),
    (RELATED, H_SAME): ("R07", R.SIMILAR), (RELATED, H_PARTIAL): ("R08", R.SIMILAR), (RELATED, H_DIFF): ("R09", R.DISJOINT),
    (NONE, H_SAME): ("R10", R.ALTERNATIVE), (NONE, H_PARTIAL): ("R11", R.ALTERNATIVE), (NONE, H_DIFF): ("R12", R.DISJOINT),
}
UNKNOWN_RULES = {
    "U01": "WHAT missing or empty for at least one idea",
    "U02": "HOW missing or empty for at least one idea",
    "U03": "the deciding link is weak (modifier-only, generic heads, or score close to the threshold)",
    "U04": "the deciding elements could not be compared (no vector or no lexical entry)",
}
GENERIC = {"system", "device", "structure", "element", "thing", "object", "unit", "tool", "item", "part",
           "solution", "idea", "product", "equipment", "material", "building", "machine", "means", "mechanism"}
RANK = {SAME: 3, HIER: 2, RELATED: 1, NONE: 0}
SAME_L = (LinkType.EQUALS, LinkType.SYNONYM)
HIER_L = (LinkType.SUBCLASS, LinkType.SUPERCLASS)


def rules_table() -> list[dict]:
    rows = [{"rule_id": rid, "WHAT": w, "HOW": h, "output": rel.value} for (w, h), (rid, rel) in TABLE.items()]
    rows[5]["output"] = "disjoint (default; 'similar' with rules_v2.hier_different=similar)"
    rows += [{"rule_id": k, "WHAT": "-", "HOW": "-", "output": "unknown", "condition": v} for k, v in UNKNOWN_RULES.items()]
    return rows


class RuleEngineV2:
    version = "v2"

    def __init__(self, cascade: Cascade, cfg: dict):
        self.cascade = cascade
        self.cfg = cfg
        c = cfg.get("rules_v2", {})
        self.margin = float(c.get("margin", 0.03))
        self.abstain = bool(c.get("abstain", True))
        self.links: list[Link] = []
        self.weak: list[str] = []

    # ---------------------------------------------------------------- links
    def _link(self, a, b, pos="n") -> Link:
        l = self.cascade.link(a, b, pos)
        self.links.append(l)
        return l

    def _is_weak(self, l: Link) -> str:
        if l.link == LinkType.NO_LINK:
            return ""
        call = next((c for c in l.calls if c.matcher == l.matcher), None)
        if call and "via modifier" in call.detail:
            return f"'{l.term1}'~'{l.term2}' linked only through a modifier"
        if call and call.score is not None and call.threshold is not None and call.score - call.threshold < self.margin:
            return f"'{l.term1}'~'{l.term2}' score {call.score} is within {self.margin} of the threshold {call.threshold}"
        h1, h2 = head_noun(l.term1).lower(), head_noun(l.term2).lower()
        if l.link in SAME_L + HIER_L and h1 in GENERIC and h2 in GENERIC and \
                len(content_words(l.term1)) <= 1 and len(content_words(l.term2)) <= 1:
            return f"'{l.term1}'~'{l.term2}' are generic terms"
        return ""

    @staticmethod
    def _level(l: Link) -> str:
        return SAME if l.link in SAME_L else HIER if l.link in HIER_L else RELATED if l.link == LinkType.SIMILAR else NONE

    def _best(self, pairs, pos="n"):
        links = [self._link(a, b, p) for a, b, p in pairs if a and b]
        if not links:
            return NONE, None
        best = max(links, key=lambda l: RANK[self._level(l)])
        return self._level(best), best

    # ---------------------------------------------------------------- Step A: WHAT evidence
    def what_level(self, a: Element, b: Element):
        if a.is_triple and b.is_triple:
            s = self._link(a.subject, b.subject, "n")
            v = self._link(a.predicate, b.predicate, "v")
            o = self._link(a.object, b.object, "n")
            ls, lo = self._level(s), self._level(o)
            v_ok = v.link in SAME_L + (LinkType.SIMILAR,)
            if ls == SAME and lo == SAME and v_ok:
                return SAME, None, {"S": ls, "V": "VR" if v_ok else "VD", "O": lo}
            if HIER in (ls, lo) and NONE not in (ls, lo) and v_ok:
                return HIER, s if ls == HIER else o, {"S": ls, "V": "VR", "O": lo}
            if ls != NONE or lo != NONE:
                deciding = s if RANK[ls] >= RANK[lo] else o
                return RELATED, deciding, {"S": ls, "V": "VR" if v_ok else "VD", "O": lo}
            return NONE, None, {"S": ls, "V": "VR" if v_ok else "VD", "O": lo}
        terms = lambda e: [e.subject, e.object] if e.is_triple else [e.text]
        pos = "s" if T.SW in (a.type, b.type) else "n"
        lvl, link = self._best([(x, y, pos) for x in terms(a) for y in terms(b)])
        if (a.is_triple or b.is_triple) and lvl == SAME:
            lvl = HIER          # a triple and a single term: the triple specialises the term
        if pos == "s" and lvl in (SAME, HIER):
            lvl = RELATED       # a sequence of words matched by similarity is only related
        return lvl, link, {"link": link.link.value if link else "no_link"}

    # ---------------------------------------------------------------- Step B: HOW evidence
    def how_level(self, a: Element, b: Element):
        if a.is_triple and b.is_triple:     # the subject of a HOW is the artefact (already in WHAT): not used
            v = self._link(a.predicate, b.predicate, "v")
            o = self._link(a.object, b.object, "n")
            v_ok = v.link in SAME_L + (LinkType.SIMILAR,)
            o_ok = o.link != LinkType.NO_LINK
            lvl = H_SAME if v_ok and o_ok else H_PARTIAL if v_ok or o_ok else H_DIFF
            deciding = o if o_ok and not v_ok else v
            return lvl, deciding, {"HOW_V": "VR" if v_ok else "VD", "HOW_O": "OR" if o_ok else "OD"}
        parts = lambda e: [e.object, e.predicate] if e.is_triple else [e.text]
        pairs = [(x, y, "s") for x in parts(a) for y in parts(b)]
        lvl, link = self._best(pairs)
        if lvl in (SAME, HIER) and not (a.is_triple or b.is_triple):
            out = H_SAME
        elif lvl != NONE:
            out = H_PARTIAL
        else:
            out = H_DIFF
        return out, link, {"HOW_link": link.link.value if link else "no_link"}

    # ---------------------------------------------------------------- decision
    def decide(self, id1, id2, w1: Element, w2: Element, h1: Element, h2: Element) -> Decision:
        self.links = []
        notes = []
        empty = lambda e: e.type == T.EMPTY
        if empty(w1) or empty(w2):
            return self._unknown("U01", id1, id2, w1, w2, h1, h2, {}, ["WHAT missing"])
        wl, wlink, wcodes = self.what_level(w1, w2)
        if empty(h1) or empty(h2):
            if self.abstain:
                return self._unknown("U02", id1, id2, w1, w2, h1, h2, {"WHAT": wl, **wcodes}, ["HOW missing"])
            hl, hlink, hcodes = H_DIFF, None, {}
        else:
            hl, hlink, hcodes = self.how_level(h1, h2)
        rid, rel = TABLE[(wl, hl)]
        if rid == "R06":            # a taxonomic link alone, with different functions, is no relation evidence
            rel = R.SIMILAR if self.cfg.get("rules_v2", {}).get("hier_different", "disjoint") == "similar" else R.DISJOINT
        codes = {"WHAT": wl, "HOW": hl, **wcodes, **hcodes}

        # Step C: weak evidence. The deciding link is the one that moved the pair away from disjoint.
        deciding = []
        if rel != R.DISJOINT:
            if wl != NONE and wlink is not None:
                deciding.append(wlink)
            if hl != H_DIFF and hlink is not None and wl == NONE:
                deciding.append(hlink)
        weak = [w for w in (self._is_weak(l) for l in deciding) if w]
        if self.abstain and weak and len(weak) == len(deciding):
            return self._unknown("U03", id1, id2, w1, w2, h1, h2, {**codes, "would_be": rel.value, "rule": rid}, weak)
        if self.abstain and rel == R.DISJOINT:
            def blind(l):
                calls = [c for c in l.calls if c.matcher != "terminology"]
                return bool(calls) and all("no vector" in c.detail or "not found in WordNet" in c.detail
                                           or "not applied" in c.detail for c in calls)
            uncomparable = [l for l in self.links if blind(l)]
            if uncomparable and len(uncomparable) == len(self.links):
                return self._unknown("U04", id1, id2, w1, w2, h1, h2, codes,
                                     [f"'{l.term1}'~'{l.term2}' could not be compared" for l in uncomparable])
        notes += weak
        direction = ""
        if rel == R.GENERALISE_DETAIL and wlink is not None:
            # term1 of the link comes from idea 1: SUBCLASS means idea 1 is the more specific one
            sub = wlink.link == LinkType.SUBCLASS
            if w1.is_triple and not w2.is_triple:
                sub = True
            elif w2.is_triple and not w1.is_triple:
                sub = False
            direction = f"{id1} details {id2} ({id2} generalises {id1})" if sub else f"{id2} details {id1} ({id1} generalises {id2})"
        return Decision(idea1=id1, idea2=id2, relationship=rel, rule_id=rid,
                        rule_text=f"{rid} [v2]: WHAT {wl}, HOW {hl} -> {rel.value}", direction=direction,
                        how_same=hl == H_SAME, how_rule_id=f"HOW-{hl}",
                        elements=self._elements(w1, w2, h1, h2), codes=codes,
                        links=[l.to_dict() for l in self.links], default_used=False, notes=notes)

    def _unknown(self, rid, id1, id2, w1, w2, h1, h2, codes, notes) -> Decision:
        return Decision(idea1=id1, idea2=id2, relationship=R.UNKNOWN, rule_id=rid,
                        rule_text=f"{rid} [v2]: {UNKNOWN_RULES[rid]} -> unknown (abstain)", direction="",
                        how_same=False, how_rule_id="-", elements=self._elements(w1, w2, h1, h2), codes=codes,
                        links=[l.to_dict() for l in self.links], default_used=False, notes=notes)

    @staticmethod
    def _elements(w1, w2, h1, h2):
        return {"idea1": {"WHAT": w1.to_dict(), "HOW": h1.to_dict()}, "idea2": {"WHAT": w2.to_dict(), "HOW": h2.to_dict()}}
