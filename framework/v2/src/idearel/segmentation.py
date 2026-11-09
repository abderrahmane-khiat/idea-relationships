"""Step 1 - pattern extraction: split a free-text idea into WHAT / HOW / WHEN.

Segmenters
    "simple"  split at the first comma or relative pronoun (version 1, used by the paper's pipeline here)
    "syntax"  spaCy-based (version 2): WHEN clauses first, then the artefact noun phrase as WHAT,
              modifier fragments attached to WHAT, the functional clauses as HOW
    "ollama"  a local LLM (Ollama) asked for JSON {what, how, when}; falls back to "syntax"

`evaluate_segmenter()` scores a segmenter against the manual patterns of data/ideas.csv.
"""
from __future__ import annotations

import json
import re

from .text import clean, content_words, split_free_text

WHEN_MARKERS = r"(in case of|in the case of|in the event of|in an emergency|in case|whenever|when|if|during|once|as soon as|while)"
WHEN_RE = re.compile(rf"(?:^|[,;]\s*|\s)(?P<w>{WHEN_MARKERS}\b[^,;.]*)", re.I)
REL_RE = re.compile(r"\b(that|which|who)\b", re.I)
LEAD_HOW = re.compile(r"^(it|they|this|these|those|the \w+)\b", re.I)
EMPTY_WHEN = re.compile(r"not explicitly specified", re.I)


def _nlp():
    from .extraction.spacy_extractor import get_nlp
    return get_nlp()


def _has_verb(fragment: str) -> bool:
    doc = _nlp()(fragment)
    return any(t.pos_ in ("VERB", "AUX") and t.tag_ not in ("VBN",) and t.dep_ not in ("amod", "acl") for t in doc) or \
        any(t.tag_ == "VBG" and t.i == 0 for t in doc)


def _modifier(fragment: str) -> bool:
    """'in each appartement', 'with their own power supply', 'placed on the roof': no finite verb, attach to WHAT."""
    doc = _nlp()(fragment)
    if not len(doc):
        return False
    if doc[0].pos_ == "ADP" and doc[0].lower_ not in ("by", "for", "to"):
        return not any(t.pos_ == "VERB" and t.tag_ in ("VBZ", "VBP", "VBD") for t in doc)
    if doc[0].tag_ == "VBN" and not any(t.tag_ in ("VBZ", "VBP", "VBD") for t in doc):
        return doc[0].lower_ in ("placed", "attached", "located", "installed", "mounted", "hanging", "equipped")
    return doc[0].lower_ in ("hanging", "equipped")


def segment_syntax(text: str) -> dict:
    t = clean(text).rstrip(".")
    # 1. WHEN: conditional / temporal clauses
    when = []
    for m in WHEN_RE.finditer(t):
        if m.group("w").lower().startswith(("if", "when", "whenever", "in case", "in the case", "in the event",
                                            "in an emergency", "during", "as soon as", "once", "while")):
            when.append(m.group("w").strip())
    for w in when:
        t = t.replace(w, " ")
    t = re.sub(r"\s*,\s*,", ",", re.sub(r"\s+", " ", t)).strip(" ,")
    # 2. WHAT: first segment; split it if it contains a relative clause or a finite verb
    segs = [s.strip() for s in re.split(r"\s*[,;]\s*|\.\s+", t) if s.strip()]
    if not segs:
        return {"what": "", "how": "", "when": "; ".join(when)}
    first, rest = segs[0], segs[1:]
    m = REL_RE.search(first)
    if m and m.start() > 0:
        rest = [first[m.start():]] + rest
        first = first[:m.start()].strip()
    else:
        doc = _nlp()(first)
        root = [tok for tok in doc if tok.dep_ == "ROOT"]
        if root and root[0].pos_ in ("VERB", "AUX") and root[0].tag_ != "VBN" and root[0].i > 0 and \
                any(c.dep_ in ("nsubj", "nsubjpass") for c in root[0].children):
            subj = next(c for c in root[0].children if c.dep_ in ("nsubj", "nsubjpass"))
            end = max(x.i for x in subj.subtree) + 1
            if end < len(doc):
                rest = [doc[end:].text] + rest
                first = doc[:end].text
    # 3. attach modifier fragments (no finite verb) to WHAT, the rest is HOW
    what = [first]
    while rest and _modifier(rest[0]):
        what.append(rest.pop(0))
    how = ", ".join(rest)
    return {"what": ", ".join(what), "how": how, "when": "; ".join(when)}


def segment_simple(text: str) -> dict:
    w, h = split_free_text(text)
    return {"what": w, "how": h, "when": ""}


PROMPT = ("Split the idea into three patterns. WHAT: the artefact or concept proposed (short noun phrase). "
          "HOW: how it works (its functions). WHEN: the situation or condition, empty if none. "
          "Copy words from the idea; do not add information. Answer only with JSON "
          '{{"what": "...", "how": "...", "when": "..."}}.\nIdea: {text}')


def segment_ollama(text: str, cfg: dict) -> dict:
    import urllib.request
    c = cfg.get("ollama", {})
    body = json.dumps({"model": c.get("model", "llama3.1"), "prompt": PROMPT.format(text=text),
                       "stream": False, "format": "json", "options": {"temperature": 0}}).encode()
    try:
        req = urllib.request.Request(c.get("url", "http://localhost:11434") + "/api/generate", body,
                                     {"Content-Type": "application/json"})
        ans = json.loads(json.loads(urllib.request.urlopen(req, timeout=60).read())["response"])
        return {k: str(ans.get(k, "")).strip() for k in ("what", "how", "when")}
    except Exception:
        return segment_syntax(text)


def segment(text: str, method: str = "syntax", cfg: dict | None = None) -> dict:
    if method == "simple":
        return segment_simple(text)
    if method == "ollama":
        return segment_ollama(text, cfg or {})
    return segment_syntax(text)


# ------------------------------------------------------------------ evaluation against manual patterns
def _bag(s: str) -> list[str]:
    if not s or EMPTY_WHEN.search(s):
        return []
    return content_words(s)


def token_f1(pred: str, gold: str) -> float | None:
    p, g = _bag(pred), _bag(gold)
    if not g and not p:
        return None              # both empty: not scored
    if not g or not p:
        return 0.0
    from collections import Counter
    common = sum((Counter(p) & Counter(g)).values())
    if not common:
        return 0.0
    P, R = common / len(p), common / len(g)
    return 2 * P * R / (P + R)


def evaluate_segmenter(ideas, method="syntax", cfg=None) -> dict:
    """Token-level F1 (content words) per pattern, macro-averaged over ideas.

    Ideas whose manual pattern is not derivable from the text (less than half of the content words of its WHAT or HOW
    occur in the text; WHEN is often inferred and is not checked) are reported separately: their gold pattern was written from another version of the idea.
    """
    rows, scores = [], {"what": [], "how": [], "when": []}
    for i in ideas.values():
        seg = segment(i.text, method, cfg)
        text_words = set(_bag(i.text))
        row = {"Idea_ID": i.id, "text": i.text}
        derivable = True
        for k, gold in (("what", i.what), ("how", i.how), ("when", i.when)):
            g = _bag(gold)
            if k != "when" and g and sum(w in text_words for w in g) / len(g) < 0.5:
                derivable = False
            row[f"pred_{k}"], row[f"gold_{k}"] = seg[k], gold
            row[f"f1_{k}"] = token_f1(seg[k], gold)
        row["gold_derivable"] = derivable
        rows.append(row)
        if derivable:
            for k in scores:
                if row[f"f1_{k}"] is not None:
                    scores[k].append(row[f"f1_{k}"])
    mean = lambda v: round(sum(v) / len(v), 3) if v else None
    return {"method": method, "n_ideas": len(rows), "n_scored": sum(r["gold_derivable"] for r in rows),
            "f1": {k: mean(v) for k, v in scores.items()},
            "f1_at_least_0.8": {k: round(sum(x >= 0.8 for x in v) / len(v), 3) if v else None for k, v in scores.items()},
            "rows": rows}
