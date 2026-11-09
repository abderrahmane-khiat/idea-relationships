"""Step 2: element identification (triple / single term / sequence of words).

Available extractors (choose with config key "extractor"):
    spacy      - dependency-based triple extraction with spaCy (default, offline)
    corenlp    - Stanford CoreNLP OpenIE via a local CoreNLP server (as in the paper)
    adelie     - ADELIE LLM for open information extraction (local, HuggingFace)
    ollama     - any local LLM served by Ollama (no API key)
    heuristic  - pure-Python fallback with NLTK part-of-speech tags
    oracle     - elements supplied by a human (oracle experiment, Reviewer 1 comment 7)
"""
from __future__ import annotations

from .base import Extractor, classify_without_triple
from .heuristic import HeuristicExtractor
from .oracle import OracleExtractor


def make_extractor(name: str, cfg: dict) -> Extractor:
    name = (name or "spacy").lower()
    if name == "spacy":
        from .spacy_extractor import SpacyExtractor
        return SpacyExtractor(cfg)
    if name == "corenlp":
        from .corenlp_extractor import CoreNLPExtractor
        return CoreNLPExtractor(cfg)
    if name == "adelie":
        from .llm_extractor import AdelieExtractor
        return AdelieExtractor(cfg)
    if name == "ollama":
        from .llm_extractor import OllamaExtractor
        return OllamaExtractor(cfg)
    if name == "heuristic":
        return HeuristicExtractor(cfg)
    if name == "oracle":
        return OracleExtractor(cfg)
    raise ValueError(f"unknown extractor {name!r}")


__all__ = ["Extractor", "make_extractor", "classify_without_triple", "HeuristicExtractor", "OracleExtractor"]
