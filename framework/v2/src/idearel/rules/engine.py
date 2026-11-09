"""Rule engine: applies the 13 HOW rules, then the 41 WHAT rules (Algorithm 1 generalised to all cases).

Element pairs are put in a canonical order (triple < single term < sequence of words); when the
ideas are swapped, the direction of generalise/detail is reported for the original order.
"""
from __future__ import annotations

from ..matching.cascade import Cascade
from ..models import Decision, Element, ElementType, Link, LinkType, Relationship
from ..text import head_noun
from .catalog import RULES, rule_text

RANK = {ElementType.TRIPLE: 0, ElementType.TERM: 1, ElementType.SW: 2}
CASE = {(0, 0): "T-T", (0, 1): "T-W", (0, 2): "T-SW", (1, 1): "W-W", (1, 2): "W-SW", (2, 2): "SW-SW"}
SAME = (LinkType.EQUALS, LinkType.SYNONYM)
RELATED = (LinkType.SIMILAR, LinkType.SUBCLASS, LinkType.SUPERCLASS)


def subject_code(link: LinkType) -> str:
    return "SRS" if link in SAME else "SR" if link in RELATED else "SD"


def object_code(link: LinkType) -> str:
    return "ORS" if link in SAME else "OR" if link in RELATED else "OD"


def verb_code(link: LinkType) -> str:
    return "VR" if link in SAME + (LinkType.SIMILAR,) else "VD"     # antonym and no link -> VD


class RuleEngine:
    def __init__(self, cascade: Cascade, cfg: dict):
        self.cascade = cascade
        self.cfg = cfg
        self.links: list[Link] = []

    # ------------------------------------------------------------------ helpers
    def _link(self, a: str, b: str, pos: str = "n") -> Link:
        l = self.cascade.link(a, b, pos)
        self.links.append(l)
        return l

    def _best(self, pairs, pos="n") -> Link:
        """Strongest link among several candidate term pairs (sameAs > subclass/superclass > similar)."""
        prio = {LinkType.EQUALS: 0, LinkType.SYNONYM: 1, LinkType.SUBCLASS: 2, LinkType.SUPERCLASS: 2, LinkType.SIMILAR: 3}
        links = [self._link(a, b, pos) for a, b in pairs if a and b]
        linked = [l for l in links if l.link in prio]
        return min(linked, key=lambda l: prio[l.link]) if linked else (links[0] if links else Link("", "", LinkType.NO_LINK, ""))

    @staticmethod
    def _ordered(e1: Element, e2: Element):
        if e1.type == ElementType.EMPTY or e2.type == ElementType.EMPTY:
            return None
        swapped = RANK[e1.type] > RANK[e2.type]
        a, b = (e2, e1) if swapped else (e1, e2)
        return a, b, swapped, CASE[(RANK[a.type], RANK[b.type])]

    def _triple_codes(self, a: Element, b: Element):
        s = self._link(a.subject, b.subject, "n")
        p = self._link(a.predicate, b.predicate, "v")
        o = self._link(a.object, b.object, "n")
        return subject_code(s.link), verb_code(p.link), object_code(o.link), (s, p, o)

    # ------------------------------------------------------------------ HOW (13 rules)
    def same_how(self, h1: Element, h2: Element) -> tuple[bool, str, dict]:
        ordered = self._ordered(h1, h2)
        if ordered is None:
            same = self.cfg.get("missing_how", "different") == "same"
            return same, "H--", {"note": "HOW missing for at least one idea"}
        a, b, _, case = ordered
        if case == "T-T":
            s, v, o, _ = self._triple_codes(a, b)
            sr = "SR" if s in ("SR", "SRS") else "SD"
            orl = "OR" if o in ("OR", "ORS") else "OD"
            table = {("SR", "VR", "OR"): "H01", ("SR", "VR", "OD"): "H02", ("SR", "VD", "OR"): "H03", ("SR", "VD", "OD"): "H04",
                     ("SD", "VR", "OR"): "H05", ("SD", "VR", "OD"): "H06", ("SD", "VD", "OD"): "H07", ("SD", "VD", "OR"): "H08"}
            rid = table[(sr, v, orl)]
            mode = self.cfg.get("rules", {}).get("how_same", "appendix")
            if mode == "object":        # same HOW = the two functions act on a related target
                return orl == "OR", rid + "/obj", {"S": sr, "V": v, "O": orl}
            if mode == "any":           # same HOW = any element of the two functions is related
                return (sr == "SR" or v == "VR" or orl == "OR"), rid + "/any", {"S": sr, "V": v, "O": orl}
            return RULES[rid][3], rid, {"S": sr, "V": v, "O": orl}
        if case == "T-W":
            l = self._best([(a.subject, b.text), (a.object, b.text)])
            return l.link.related, "H09", {"link": l.link.value}
        if case == "T-SW":
            l = self._link(a.as_text(), b.text, "s")
            return l.link.related, "H10", {"link": l.link.value}
        if case == "W-W":
            l = self._link(a.text, b.text)
            return l.link.related, "H11", {"link": l.link.value}
        if case == "W-SW":
            l = self._link(a.text, b.text, "s")
            return l.link.related, "H12", {"link": l.link.value}
        l = self._link(a.text, b.text, "s")
        return l.link.related, "H13", {"link": l.link.value}

    # ------------------------------------------------------------------ WHAT (41 rules)
    def decide(self, id1: str, id2: str, w1: Element, w2: Element, h1: Element, h2: Element) -> Decision:
        self.links = []
        h, how_rule, how_codes = self.same_how(h1, h2)
        ordered = self._ordered(w1, w2)
        if ordered is None:
            return self._finish(id1, id2, Relationship.DISJOINT, "Default", h, how_rule, {}, w1, w2, h1, h2, default=True,
                                notes=["WHAT missing: no relation evidence"])
        a, b, swapped, case = ordered
        codes = {"case": case, "HOW": "same" if h else "different", **{f"HOW_{k}": v for k, v in how_codes.items()}}
        direction = ""

        if case == "T-W":
            l = self._best([(a.subject, b.text), (a.object, b.text)])
            codes["link"] = l.link.value
            rid = ("W01" if h else "W02") if l.link.related else ("W03" if h else "W04")
            if rid == "W01":       # the triple specialises the single term
                direction = "specific details general"
        elif case == "T-SW":
            l = self._link(f"{a.subject} {a.object}", b.text, "s")
            codes["link"] = l.link.value
            rid = ("W05" if h else "W06") if l.link.related else ("W07" if h else "W08")
        elif case == "T-T":
            s, v, o, _ = self._triple_codes(a, b)
            codes.update({"S": s, "V": v, "O": o})
            s_rel, o_rel = s in ("SR", "SRS"), o in ("OR", "ORS")
            if s == "SRS" and v == "VR" and o == "ORS":
                rid = "W09" if h else "W10"
            elif s_rel and v == "VR" and o_rel:
                rid = "W11" if h else "W12"
                direction = self._triple_direction(a, b) if h else ""
            elif s_rel and v == "VR":
                rid = "W13" if h else "W14"
            elif s_rel and o_rel:
                rid = "W15" if h else "W16"
            elif s_rel:
                rid = "W17"
            elif v == "VR" and o_rel:
                rid = "W18" if h else "W19"
            elif v == "VR":
                rid = "W21" if h else "W20"
            elif not o_rel:
                # Appendix B rule 8a gives alternative-solution when the HOW is the same; Algorithm 1
                # (line 7) gives disjoint. Configurable: rules.sd_vd_od = "appendix" | "algorithm1".
                strict = self.cfg.get("rules", {}).get("sd_vd_od", "appendix") == "algorithm1"
                rid = "W23" if (strict or not h) else "W22"
            else:
                rid = "W24" if h else "W25"
        elif case == "W-W":
            l = self._link(a.text, b.text)
            codes["link"] = l.link.value
            if l.link in (LinkType.SUBCLASS, LinkType.SUPERCLASS):
                rid = "W26" if h else "W27"
                if h:
                    direction = "first details second" if l.link == LinkType.SUBCLASS else "second details first"
            elif l.link in SAME:
                rid = "W28" if h else "W29"
            elif l.link == LinkType.SIMILAR:
                rid = "W30" if h else "W31"
            else:
                rid = "W32" if h else "W33"
        elif case == "W-SW":
            l = self._link(a.text, b.text, "s")
            codes["link"] = l.link.value
            rid = ("W34" if h else "W35") if l.link.related else ("W36" if h else "W37")
        else:
            l = self._link(a.text, b.text, "s")
            codes["link"] = l.link.value
            rid = ("W38" if h else "W39") if l.link.related else ("W40" if h else "W41")

        rel = RULES[rid][3]
        return self._finish(id1, id2, rel, rid, h, how_rule, codes, w1, w2, h1, h2,
                            direction=self._direction_text(direction, swapped, id1, id2) if rel == Relationship.GENERALISE_DETAIL else "")

    def _triple_direction(self, a: Element, b: Element) -> str:
        """In rule 2a the idea whose subject/object is the subclass is the more specific one."""
        for x, y in ((a.subject, b.subject), (a.object, b.object)):
            l = self.cascade.link(x, y, "n")
            if l.link == LinkType.SUBCLASS:
                return "first details second"
            if l.link == LinkType.SUPERCLASS:
                return "second details first"
        return ""

    @staticmethod
    def _direction_text(direction: str, swapped: bool, id1: str, id2: str) -> str:
        if not direction:
            return ""
        first, second = (id2, id1) if swapped else (id1, id2)
        if direction == "specific details general":      # triple (first) details single term (second)
            return f"{first} details {second} ({second} generalises {first})"
        if direction == "first details second":
            return f"{first} details {second} ({second} generalises {first})"
        return f"{second} details {first} ({first} generalises {second})"

    def _finish(self, id1, id2, rel, rid, h, how_rule, codes, w1, w2, h1, h2, direction="", default=False, notes=None) -> Decision:
        return Decision(idea1=id1, idea2=id2, relationship=rel, rule_id=rid,
                        rule_text=rule_text(rid) if rid in RULES else "Default: no relation evidence found",
                        direction=direction, how_same=h, how_rule_id=how_rule,
                        elements={"idea1": {"WHAT": w1.to_dict(), "HOW": h1.to_dict()},
                                  "idea2": {"WHAT": w2.to_dict(), "HOW": h2.to_dict()}},
                        codes=codes, links=[l.to_dict() for l in self.links], default_used=default, notes=notes or [])


def what_head(element: Element) -> str:
    return element.subject if element.is_triple else head_noun(element.text)
