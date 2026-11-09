"""End-to-end tests with the real local resources (WordNet, spaCy, word vectors)."""
import json

import pytest

from idearel import Framework, Idea, Relationship, load_config


@pytest.fixture(scope="module")
def fw():
    return Framework(load_config())


def test_paper_duplicate_example(fw):
    d = fw.compare(Idea("A", "", "Window composed of heat-sensitive material", "indicates the exit path"),
                   Idea("B", "", "Window made of heat-sensitive material", "shows the exit path"))
    assert d.relationship == Relationship.DUPLICATE and d.rule_id == "W09"


def test_paper_generalise_example(fw):
    d = fw.compare(Idea("A", "", "Window", "indicates the escape route"),
                   Idea("B", "", "Structure element", "shows the exit path"))
    assert d.relationship == Relationship.GENERALISE_DETAIL and "A details B" in d.direction


def test_audit_trail_is_complete(fw):
    d = fw.compare(Idea("A", "", "waterproof carpet", "it absorbs the water"),
                   Idea("B", "", "waterproof floor", "it absorbs the water"))
    out = d.to_dict()
    assert out["rule_id"] and out["how_rule_id"] and out["links"]
    assert all(c["matcher"] for l in out["links"] for c in l["calls"])
    json.dumps(out)


def test_free_text_is_segmented(fw):
    d = fw.compare(Idea("A", "Rescue Indication floor, that lights up to show the exit path"),
                   Idea("B", "Rescue Indication wall, that lights up to show the exit path"))
    assert d.elements["idea1"]["HOW"]["type"] != "empty"


def test_oracle_overrides_extraction():
    oracle = {"A": {"WHAT": {"type": "single_term", "text": "window"}, "HOW": {"type": "single_term", "text": "exit path"}},
              "B": {"WHAT": {"type": "single_term", "text": "window"}, "HOW": {"type": "single_term", "text": "escape route"}}}
    d = Framework(load_config(), oracle).compare(Idea("A", "", "x", "x"), Idea("B", "", "y", "y"))
    assert d.elements["idea1"]["WHAT"]["source"] == "oracle"
    assert d.relationship == Relationship.DUPLICATE


def test_ablation_switch():
    cfg = load_config(overrides={"cascade.enabled": "terminology"})
    fw = Framework(cfg)
    assert fw.cascade.order == ["terminology"]


def test_heuristic_extractor_runs():
    fw = Framework(load_config(overrides={"extractor": "heuristic"}))
    d = fw.compare(Idea("A", "", "Window composed of heat-sensitive material", "indicates the exit path"),
                   Idea("B", "", "Window made of heat-sensitive material", "shows the exit path"))
    assert d.relationship in set(Relationship)


def test_segmenter_syntax():
    from idearel.segmentation import segment
    s = segment("carbon monoxide detector, in each appartement, that detects and absorbs carbon monoxide if there is a leak")
    assert s["what"].startswith("carbon monoxide detector") and "in each appartement" in s["what"]
    assert s["how"].startswith("that detects") and s["when"].startswith("if there is")


def test_v2_pipeline_runs():
    fw = Framework(load_config(overrides={"rules_version": "v2"}))
    d = fw.compare(Idea("A", "", "waterproof carpet", "that absorbs water"),
                   Idea("B", "", "waterproof floor", "that absorbs water"))
    assert d.rule_id.startswith(("R", "U"))
