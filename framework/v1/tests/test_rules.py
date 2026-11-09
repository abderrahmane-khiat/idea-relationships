"""Deterministic tests of all 54 rules: the cascade is replaced by a stub, so only the rule logic is tested.

In the stub, the link between two terms is written in the second term: e.g. ("window", "subclass")
means the cascade returns 'subclass'. This lets every combination of Table 1 codes be produced.
"""
import itertools

import pytest

from idearel.models import Element, ElementType as T, Link, LinkType, Relationship as R
from idearel.rules import HOW_RULES, WHAT_RULES, RuleEngine


class StubCascade:
    order = ["stub"]

    def link(self, a, b, pos="n"):
        try:
            lt = LinkType(b.split()[-1])
        except ValueError:
            lt = LinkType.NO_LINK
        return Link(a, b, lt, "stub", [])


def engine(**cfg):
    return RuleEngine(StubCascade(), {"missing_how": "different", **cfg})


def tri(s, p, o):
    return Element(T.TRIPLE, subject=s, predicate=p, object=o)


def term(t):
    return Element(T.TERM, text=t)


def sw(t):
    return Element(T.SW, text=t)


SAME_HOW = (sw("how"), sw("how equals"))
DIFF_HOW = (sw("how"), sw("how no_link"))

S_LINK = {"SRS": "equals", "SR": "subclass", "SD": "no_link"}
V_LINK = {"VR": "synonym", "VD": "antonym"}
O_LINK = {"ORS": "synonym", "OR": "similar", "OD": "no_link"}


def expected_tt(s, v, o, h):
    s_rel, o_rel = s != "SD", o != "OD"
    if s == "SRS" and v == "VR" and o == "ORS":
        return "W09" if h else "W10"
    if s_rel and v == "VR" and o_rel:
        return "W11" if h else "W12"
    if s_rel and v == "VR":
        return "W13" if h else "W14"
    if s_rel and o_rel:
        return "W15" if h else "W16"
    if s_rel:
        return "W17"
    if v == "VR" and o_rel:
        return "W18" if h else "W19"
    if v == "VR":
        return "W21" if h else "W20"
    if not o_rel:
        return "W22" if h else "W23"
    return "W24" if h else "W25"


@pytest.mark.parametrize("s,v,o,h", list(itertools.product(S_LINK, V_LINK, O_LINK, [True, False])))
def test_triple_triple(s, v, o, h):
    e = engine()
    w1, w2 = tri("a", "p", "b"), tri(f"x {S_LINK[s]}", f"q {V_LINK[v]}", f"y {O_LINK[o]}")
    h1, h2 = SAME_HOW if h else DIFF_HOW
    d = e.decide("I1", "I2", w1, w2, h1, h2)
    assert d.rule_id == expected_tt(s, v, o, h)
    assert d.relationship == dict((r[0], r[3]) for r in WHAT_RULES)[d.rule_id]


@pytest.mark.parametrize("w2,h,rid", [
    (term("x subclass"), True, "W01"), (term("x similar"), False, "W02"),
    (term("x no_link"), True, "W03"), (term("x no_link"), False, "W04")])
def test_triple_term(w2, h, rid):
    d = engine().decide("I1", "I2", tri("window", "made of", "material"), w2, *(SAME_HOW if h else DIFF_HOW))
    assert d.rule_id == rid


@pytest.mark.parametrize("w2,h,rid", [
    (sw("x similar"), True, "W05"), (sw("x similar"), False, "W06"),
    (sw("x no_link"), True, "W07"), (sw("x no_link"), False, "W08")])
def test_triple_sw(w2, h, rid):
    d = engine().decide("I1", "I2", tri("building", "consists of", "structure"), w2, *(SAME_HOW if h else DIFF_HOW))
    assert d.rule_id == rid


@pytest.mark.parametrize("link,h,rid", [
    ("subclass", True, "W26"), ("superclass", False, "W27"), ("equals", True, "W28"), ("synonym", False, "W29"),
    ("similar", True, "W30"), ("similar", False, "W31"), ("no_link", True, "W32"), ("no_link", False, "W33")])
def test_term_term(link, h, rid):
    d = engine().decide("I1", "I2", term("window"), term(f"x {link}"), *(SAME_HOW if h else DIFF_HOW))
    assert d.rule_id == rid


@pytest.mark.parametrize("link,h,rid", [
    ("similar", True, "W34"), ("similar", False, "W35"), ("no_link", True, "W36"), ("no_link", False, "W37")])
def test_term_sw(link, h, rid):
    d = engine().decide("I1", "I2", term("window"), sw(f"x {link}"), *(SAME_HOW if h else DIFF_HOW))
    assert d.rule_id == rid


@pytest.mark.parametrize("link,h,rid", [
    ("similar", True, "W38"), ("similar", False, "W39"), ("no_link", True, "W40"), ("no_link", False, "W41")])
def test_sw_sw(link, h, rid):
    d = engine().decide("I1", "I2", sw("flying robots"), sw(f"x {link}"), *(SAME_HOW if h else DIFF_HOW))
    assert d.rule_id == rid


@pytest.mark.parametrize("s,v,o,rid,same", [
    ("SR", "VR", "OR", "H01", True), ("SR", "VR", "OD", "H02", False), ("SR", "VD", "OR", "H03", True),
    ("SR", "VD", "OD", "H04", False), ("SD", "VR", "OR", "H05", True), ("SD", "VR", "OD", "H06", False),
    ("SD", "VD", "OD", "H07", False), ("SD", "VD", "OR", "H08", False)])
def test_how_triple_rules(s, v, o, rid, same):
    h2 = tri(f"x {S_LINK[s]}", f"q {V_LINK[v]}", f"y {O_LINK[o]}")
    got_same, got_rid, _ = engine().same_how(tri("a", "p", "b"), h2)
    assert (got_same, got_rid) == (same, rid)


@pytest.mark.parametrize("h1,h2,rid", [
    (tri("signal", "is on", "outside"), term("x similar"), "H09"),
    (tri("signal", "is on", "outside"), sw("x similar"), "H10"),
    (term("exit path"), term("x synonym"), "H11"),
    (term("position"), sw("x similar"), "H12"),
    (sw("sending info"), sw("x similar"), "H13")])
def test_how_other_rules(h1, h2, rid):
    same, got, _ = engine().same_how(h1, h2)
    assert got == rid and same
    same2, got2, _ = engine().same_how(h1, Element(h2.type, text="x no_link", subject="x no_link",
                                                   predicate="q", object="y no_link"))
    assert got2 == rid and not same2


def test_rule_counts():
    assert len(WHAT_RULES) == 41 and len(HOW_RULES) == 13


def test_algorithm1_variant():
    w1, w2 = tri("a", "p", "b"), tri("x no_link", "q antonym", "y no_link")
    assert engine().decide("I1", "I2", w1, w2, *SAME_HOW).relationship == R.ALTERNATIVE
    assert engine(rules={"sd_vd_od": "algorithm1"}).decide("I1", "I2", w1, w2, *SAME_HOW).relationship == R.DISJOINT


def test_order_independent_and_direction():
    e = engine()
    d1 = e.decide("I1", "I2", term("window subclass"), tri("x", "p", "y"), *SAME_HOW)
    assert d1.rule_id == "W01" and "I2 details I1" in d1.direction
    d2 = e.decide("I1", "I2", term("window"), term("x subclass"), *SAME_HOW)
    assert d2.direction.startswith("I1 details I2")


def test_missing_what_is_default_disjoint():
    d = engine().decide("I1", "I2", Element(T.EMPTY), term("x"), *SAME_HOW)
    assert d.relationship == R.DISJOINT and d.default_used


@pytest.mark.parametrize("mode,codes,same", [
    ("object", ("x no_link", "q antonym", "y similar"), True),
    ("object", ("x subclass", "q synonym", "y no_link"), False),
    ("any", ("x no_link", "q synonym", "y no_link"), True),
    ("any", ("x no_link", "q antonym", "y no_link"), False)])
def test_how_same_variants(mode, codes, same):
    got, rid, _ = engine(rules={"how_same": mode}).same_how(tri("a", "p", "b"), tri(*codes))
    assert got == same and rid.endswith("/obj" if mode == "object" else "/any")
