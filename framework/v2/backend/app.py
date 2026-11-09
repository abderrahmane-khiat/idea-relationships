"""Web version: FastAPI backend that runs the framework and serves the frontend.

    idearel serve                      (or: uvicorn backend.app:app --port 8000)

Endpoints
    GET  /api/health          resources and default configuration
    GET  /api/rules           the 54 rules
    GET  /api/examples        example ideas from data/ideas.csv
    POST /api/compare         {idea1: {what, how, text}, idea2: {...}, options: {...}} -> decision with audit trail
    POST /api/extract         {what, how, options} -> elements
    POST /api/segment         {text, options} -> {what, how, when}   (Step 1 for free text)
    GET  /api/rules?version=v2  the v2 rule set (future work)
"""
from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from idearel import Framework, Idea, load_config  # noqa: E402
from idearel.config import copy_config  # noqa: E402
from idearel.extraction.oracle import OracleExtractor  # noqa: E402
from idearel.rules import as_table  # noqa: E402
from idearel.rules.engine import what_head  # noqa: E402


class IdeaIn(BaseModel):
    id: str = ""
    text: str = ""
    what: str = ""
    how: str = ""
    when: str = ""
    oracle_what: Optional[dict] = None     # e.g. {"type": "triple", "subject": .., "predicate": .., "object": ..}
    oracle_how: Optional[dict] = None


class Options(BaseModel):
    extractor: str = "spacy"
    order: list[str] = Field(default_factory=lambda: ["structure", "linguistic", "content", "terminology"])
    enabled: list[str] = Field(default_factory=lambda: ["structure", "linguistic", "content", "terminology"])
    linguistic: float = 0.75
    content: float = 0.80
    terminology: float = 0.85
    implicit_how_subject: bool = True
    sd_vd_od: str = "appendix"
    rules_version: str = "v1"
    abstain: bool = True
    segmenter: str = "simple"


class CompareIn(BaseModel):
    idea1: IdeaIn
    idea2: IdeaIn
    options: Options = Options()


class ExtractIn(BaseModel):
    what: str = ""
    how: str = ""
    options: Options = Options()


BASE = load_config()


def config_from(o: Options) -> dict:
    c = copy_config(BASE)
    c["extractor"] = o.extractor
    c["cascade"] = {"order": o.order, "enabled": o.enabled}
    c["thresholds"] = {"linguistic": o.linguistic, "content": o.content, "terminology": o.terminology}
    c["implicit_how_subject"] = o.implicit_how_subject
    c.setdefault("rules", {})["sd_vd_od"] = o.sd_vd_od
    c["rules_version"] = o.rules_version
    c.setdefault("rules_v2", {})["abstain"] = o.abstain
    c["segmenter"] = o.segmenter
    return c


@lru_cache(maxsize=16)
def _framework(key: str) -> Framework:
    import json
    return Framework(json.loads(key))


def framework(o: Options) -> Framework:
    import json
    return _framework(json.dumps(config_from(o), sort_keys=True))


app = FastAPI(title="idearel", version="1.0.0", description="Interpretable detection of relationships between ideas")


@app.get("/api/health")
def health():
    return {"status": "ok", "defaults": Options().model_dump(), "extractors": ["spacy", "heuristic", "corenlp", "adelie", "ollama"]}


@app.get("/api/rules")
def rules(version: str = "v1"):
    if version == "v2":
        from idearel.rules.v2 import rules_table
        return rules_table()
    return as_table()


class SegmentIn(BaseModel):
    text: str
    options: Options = Options()


@app.post("/api/segment")
def segment_text(req: SegmentIn):
    from idearel.segmentation import segment
    return segment(req.text, req.options.segmenter if req.options.segmenter != "simple" else "syntax", config_from(req.options))


@app.get("/api/examples")
def examples():
    from idearel.evaluation import load_ideas
    try:
        ideas = load_ideas()
    except FileNotFoundError:
        return []
    return [{"id": i.id, "text": i.text, "what": i.what, "how": i.how, "when": i.when} for i in ideas.values()]


@app.post("/api/compare")
def compare(req: CompareIn):
    try:
        fw = framework(req.options)
    except Exception as e:
        raise HTTPException(400, f"cannot build the pipeline: {e}")
    oracle = {}
    for key, idea in (("IDEA1", req.idea1), ("IDEA2", req.idea2)):
        entry = {p: d for p, d in (("WHAT", idea.oracle_what), ("HOW", idea.oracle_how)) if d}
        if entry:
            oracle[key] = entry
    ideas = []
    for key, idea in (("IDEA1", req.idea1), ("IDEA2", req.idea2)):
        if not (idea.what.strip() or idea.text.strip() or (key in oracle and "WHAT" in oracle[key])):
            raise HTTPException(422, f"{key}: give the WHAT pattern (or the free text)")
        ideas.append(Idea(key, idea.text, idea.what or ("(oracle)" if key in oracle else ""), idea.how or ("(oracle)" if key in oracle and "HOW" in oracle[key] else ""), idea.when))
    extractor = fw.extractor
    if oracle:      # per-request oracle elements; the shared pipeline is not modified
        fw = Framework.__new__(Framework)
        base = framework(req.options)
        fw.cfg, fw.cascade, fw.engine, fw._elements = base.cfg, base.cascade, base.engine, {}
        fw.extractor = OracleExtractor(base.cfg, oracle, extractor)
    else:
        fw._elements = {}
    d = fw.compare(*ideas)
    return d.to_dict()


@app.post("/api/extract")
def extract(req: ExtractIn):
    fw = framework(req.options)
    w = fw.extractor.extract(req.what, "WHAT", {"idea_id": ""})
    h = fw.extractor.extract(req.how, "HOW", {"idea_id": "", "what_head": what_head(w)})
    return {"WHAT": w.to_dict(), "HOW": h.to_dict()}


FRONT = ROOT / "frontend"
app.mount("/static", StaticFiles(directory=FRONT), name="static")


@app.get("/")
def index():
    return FileResponse(FRONT / "index.html")
