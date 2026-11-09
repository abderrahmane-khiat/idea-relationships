"""Core data structures of the framework.

An idea is described by three patterns (Bullinger, 2008):
    WHAT  - what the idea is about (its purpose / object),
    HOW   - how the idea works (its mechanism),
    WHEN  - in which situation it applies (not used for matching).

Step 2 turns WHAT and HOW into an *element*: a triple <S, P, O>, a single
term, or a sequence of words. Step 3 links corresponding elements of two
ideas; Step 4 applies the 54 rules to the links.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Optional


class ElementType(str, Enum):
    TRIPLE = "triple"
    TERM = "single_term"
    SW = "sequence_of_words"
    EMPTY = "empty"


@dataclass
class Element:
    """Result of element identification for one pattern."""
    type: ElementType
    text: str = ""
    subject: str = ""
    predicate: str = ""
    object: str = ""
    source: str = ""          # extractor that produced it (spacy, corenlp, oracle, ...)

    @property
    def is_triple(self) -> bool:
        return self.type == ElementType.TRIPLE

    def as_text(self) -> str:
        if self.is_triple:
            return f"{self.subject} {self.predicate} {self.object}".strip()
        return self.text

    def to_dict(self) -> dict:
        d = asdict(self)
        d["type"] = self.type.value
        return d

    @staticmethod
    def from_dict(d: dict) -> "Element":
        t = ElementType(d.get("type", "sequence_of_words"))
        return Element(type=t, text=d.get("text", ""), subject=d.get("subject", d.get("s", "")),
                       predicate=d.get("predicate", d.get("p", "")), object=d.get("object", d.get("o", "")),
                       source=d.get("source", "oracle"))


@dataclass
class Idea:
    id: str
    text: str = ""
    what: str = ""
    how: str = ""
    when: str = ""


class LinkType(str, Enum):
    """Links returned by the matching mechanism (Section 4.3)."""
    EQUALS = "equals"
    SYNONYM = "synonym"
    SUBCLASS = "subclass"        # term1 is a subclass (more specific) of term2
    SUPERCLASS = "superclass"    # term1 is a superclass (more general) of term2
    SIMILAR = "similar"
    ANTONYM = "antonym"          # predicates only
    NO_LINK = "no_link"          # no matcher found evidence (former "disjoint")

    @property
    def related(self) -> bool:
        return self not in (LinkType.NO_LINK, LinkType.ANTONYM)


@dataclass
class MatcherCall:
    matcher: str
    term1: str
    term2: str
    score: Optional[float]
    threshold: Optional[float]
    link: LinkType
    detail: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["link"] = self.link.value
        return d


@dataclass
class Link:
    """Outcome of the cascade for one pair of terms, with the full trail."""
    term1: str
    term2: str
    link: LinkType
    matcher: str                        # matcher that established the link ("" if none)
    calls: list[MatcherCall] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"term1": self.term1, "term2": self.term2, "link": self.link.value,
                "matcher": self.matcher, "calls": [c.to_dict() for c in self.calls]}


class Relationship(str, Enum):
    DUPLICATE = "duplicate"
    GENERALISE_DETAIL = "generalise/detail"
    ALTERNATIVE = "alternative-solution"
    SIMILAR = "similar"
    DISJOINT = "disjoint"
    UNKNOWN = "unknown"          # rules v2 only: missing or weak evidence -> abstain


@dataclass
class Decision:
    """Final output for a pair of ideas, with the complete audit trail."""
    idea1: str
    idea2: str
    relationship: Relationship
    rule_id: str
    rule_text: str
    direction: str = ""                 # e.g. "IDEA1 details IDEA2" for generalise/detail
    how_same: Optional[bool] = None
    how_rule_id: str = ""
    elements: dict[str, Any] = field(default_factory=dict)
    codes: dict[str, str] = field(default_factory=dict)
    links: list[dict] = field(default_factory=list)
    default_used: bool = False
    notes: list[str] = field(default_factory=list)

    @property
    def related(self) -> bool:
        return self.relationship != Relationship.DISJOINT

    def to_dict(self) -> dict:
        d = asdict(self)
        d["relationship"] = self.relationship.value
        return d
