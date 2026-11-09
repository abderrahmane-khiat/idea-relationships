"""Rules v2: the decision table, the unknown (abstain) rules and the evidence levels, with a stub cascade."""
import itertools

import pytest

from idearel.models import Element, ElementType as T, Link, LinkType, MatcherCall, Relationship as R
from idearel.rules.v2 import TABLE, RuleEngineV2


class StubCascade:
    """The link is written as the last word of the second term; 'weak' adds a near-threshold score."""
    order = ["stub"]

    def link(self, a, b, pos="n"):
        if a == b:
            return Link(a, b, LinkType.EQUALS, "structure", [MatcherCall("structure", a, b, 1.0, None, LinkType.EQUALS, "stub")])
        words = b.split()
        weak = "weak" in words
        try:
            lt = LinkType(words[-1])
        except ValueError:
            lt = LinkType.NO_LINK
        call = MatcherCall("content", a, b, 0.81 if weak else 1.0, 0.80 if weak else None, lt, "stub")
        return Link(a, b, lt, "content" if lt != LinkType.NO_LINK else "", [call])


def eng(**c):
    return RuleEngineV2(StubCascade(), {"rules_v2": {"abstain": True, "margin": 0.03, **c}})


term = lambda t: Element(T.TERM, text=t)
sw = lambda t: Element(T.SW, text=t)
tri = lambda s, p, o: Element(T.TRIPLE, subject=s, predicate=p, object=o)
WHAT_LINK = {"SAME": "equals", "HIER": "subclass", "RELATED": "similar", "NONE": "no_link"}
HOW = {"SAME": ("p x", "q synonym", "o x", "y equals"), "PARTIAL": ("p x", "q synonym", "o x", "y no_link"),
       "DIFFERENT": ("p x", "q antonym", "o x", "y no_link")}


@pytest.mark.parametrize("w,h", list(itertools.product(WHAT_LINK, HOW)))
def test_decision_table(w, h):
    p1, p2, o1, o2 = HOW[h]
    d = eng(hier_different="similar").decide("I1", "I2", term("artefact"), term(f"thing2 {WHAT_LINK[w]}"),
                                             tri("a", p1, o1), tri("b", p2, o2))
    rid, rel = TABLE[(w, h)]
    if rid == "R06":
        rel = R.SIMILAR
    assert (d.rule_id, d.relationship) == (rid, rel)


def test_r06_default_is_disjoint():
    p1, p2, o1, o2 = HOW["DIFFERENT"]
    d = eng().decide("I1", "I2", term("window"), term("x subclass"), tri("a", p1, o1), tri("b", p2, o2))
    assert d.rule_id == "R06" and d.relationship == R.DISJOINT


def test_unknown_missing_what_and_how():
    assert eng().decide("I1", "I2", Element(T.EMPTY), term("x"), sw("h"), sw("h equals")).rule_id == "U01"
    assert eng().decide("I1", "I2", term("a"), term("x equals"), Element(T.EMPTY), sw("h")).rule_id == "U02"


def test_unknown_weak_link():
    d = eng().decide("I1", "I2", term("carpet"), term("floor weak similar"), sw("absorbs water"), sw("pours water weak similar"))
    assert d.rule_id == "U03" and d.relationship == R.UNKNOWN and d.codes["would_be"]


def test_no_abstention_when_disabled():
    d = eng(abstain=False).decide("I1", "I2", term("carpet"), term("floor weak similar"), sw("a"), sw("b weak similar"))
    assert d.relationship != R.UNKNOWN


def test_generic_terms_are_weak():
    d = eng().decide("I1", "I2", term("system"), term("system"), sw("a"), sw("b no_link"))
    # equals between generic heads -> weak; with a different HOW the cell is R03 (similar) -> abstain
    assert d.rule_id in ("U03",)


def test_generalise_direction():
    d = eng().decide("I1", "I2", term("window"), term("structure subclass"), sw("a"), sw("b equals"))
    assert d.relationship == R.GENERALISE_DETAIL and d.direction.startswith("I1 details I2")
