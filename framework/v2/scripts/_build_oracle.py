"""Builds data/oracle_ideas.json: manually curated elements for the 52 ideas of the 240 test pairs.

Curated by reading WHAT and HOW of each idea, following Table 1 of the paper:
  WHAT: the artefact as a single term, or a triple when the WHAT states a relation;
  HOW:  the main function as a triple <artefact, action, target>; a sequence of words when no action is stated.
Prepared as a draft gold standard: to be verified by the authors before it is reported.
"""
import json
from pathlib import Path

W = lambda t: {"type": "single_term", "text": t}
S = lambda t: {"type": "sequence_of_words", "text": t}
T = lambda s, p, o: {"type": "triple", "subject": s, "predicate": p, "object": o}

O = {
 "IDEA001": (T("capsule", "puts itself over", "fire"), T("capsule", "extinguishes", "fire")),
 "IDEA002": (W("flying drones"), T("drones", "pour", "water")),
 "IDEA003": (W("fire extinguisher"), T("fire extinguisher", "sprays", "carbon dioxide")),
 "IDEA004": (W("fireproof furniture"), T("furniture", "made of", "fire-resistant substance")),
 "IDEA005": (W("capsules"), T("people", "jump out of", "building")),
 "IDEA006": (W("thermal insulation doors"), T("doors", "contain", "fire")),
 "IDEA007": (W("waterproof carpet"), T("carpet", "absorbs", "water")),
 "IDEA008": (W("waterproof floor"), T("floor", "absorbs", "water")),
 "IDEA009": (W("sensory walls"), T("walls", "raise", "alarm")),
 "IDEA010": (W("carbon monoxide detector"), T("detector", "absorbs", "carbon monoxide")),
 "IDEA011": (W("absorption device"), T("device", "absorbs", "gas")),
 "IDEA012": (T("building", "has", "variable structure"), T("structure", "descends to", "ground")),
 "IDEA013": (W("evacuation alert"), T("system", "notifies", "occupants")),
 "IDEA014": (W("intelligent rescue system"), T("system", "identifies", "accidents")),
 "IDEA015": (W("water triggers"), T("triggers", "avoid", "fire propagation")),
 "IDEA016": (W("fireproof walls"), T("walls", "painted with", "fireproof substance")),
 "IDEA017": (W("table"), T("table", "changes into", "solid box")),
 "IDEA018": (W("fireproof clothing"), T("clothing", "hangs with", "fire extinguishers")),
 "IDEA019": (W("sensory walls"), T("walls", "raise", "alarm")),
 "IDEA020": (W("rescue indication floor"), T("floor", "shows", "exit path")),
 "IDEA021": (W("rescue drones"), T("drones", "guide", "people")),
 "IDEA022": (W("rescue parachutes"), S("escape route from high-rise buildings")),
 "IDEA023": (W("rescue robots"), S("activated on the different floors")),
 "IDEA024": (W("smart watch"), T("watch", "predicts", "danger")),
 "IDEA025": (W("rescue closets"), T("closet", "turns into", "escape elevator")),
 "IDEA026": (W("intelligent system"), S("early detection of threats and rapid evacuation")),
 "IDEA027": (W("fire department navigation"), T("system", "identifies", "seat of fire")),
 "IDEA028": (W("emergency radio"), S("instructions about necessary behavior")),
 "IDEA029": (W("solid exterior space"), T("balcony", "turns into", "panic room")),
 "IDEA030": (W("rescue closets"), T("closet", "used as", "escape elevator")),
 "IDEA031": (W("magnet panels"), T("panels", "guide", "persons")),
 "IDEA032": (T("building", "consists of", "variable structure"), T("structure", "descends to", "ground")),
 "IDEA033": (W("air bag suits"), T("suits", "save", "people")),
 "IDEA034": (W("fireproof suits"), T("suits", "supplied with", "oxygen bags")),
 "IDEA035": (W("clothes"), T("clothes", "cover", "body")),
 "IDEA036": (W("pillows"), T("pillows", "wake up", "sleeper")),
 "IDEA037": (W("carbon monoxide sensitive cells"), T("cells", "cut", "electricity")),
 "IDEA038": (W("evacuation application"), T("application", "forwards", "information")),
 "IDEA039": (W("steel doors"), T("doors", "close", "automatically")),
 "IDEA040": (W("staircase"), T("staircase", "provides", "exit")),
 "IDEA041": (W("heat wave mitigation"), T("building", "regulates", "temperature")),
 "IDEA042": (W("tunnel system"), T("tunnel", "leads", "people")),
 "IDEA043": (W("rescue pipelines"), T("pipelines", "serve as", "escape route")),
 "IDEA044": (W("position information"), T("system", "displays", "evacuation routes")),
 "IDEA045": (W("scale detection system"), T("system", "blocks", "elevator")),
 "IDEA046": (W("protection helmet"), T("helmet", "transforms into", "airbags")),
 "IDEA047": (W("retractable stairs"), T("stairs", "used to escape from", "building")),
 "IDEA048": (W("robots"), T("robots", "neutralize", "terrorist")),
 "IDEA049": (W("toboggans"), S("rapid evacuation through toboggan rides")),
 "IDEA050": (W("oxygen masks"), T("masks", "dropped down", "automatically")),
 "IDEA051": (W("intelligent system"), T("system", "predicts", "danger")),
 "IDEA052": (W("intelligent alarm system"), T("system", "predicts", "dangerous situations")),
}
out = {k: {"WHAT": w, "HOW": h} for k, (w, h) in O.items()}
path = Path(__file__).resolve().parents[1] / "data" / "oracle_ideas.json"
path.write_text(json.dumps(out, indent=2), encoding="utf-8")
print(f"wrote {path} ({len(out)} ideas)")
