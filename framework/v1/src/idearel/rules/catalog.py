"""The complete rule set (Appendix B of the paper): 41 WHAT rules and 13 HOW rules.

Notation (Table 1): S = subject, V = predicate, O = object, W = single term, SW = sequence of words.
    SRS / ORS : same subject / object (equal or synonym)
    SR  / OR  : related subject / object (similar, subclass or superclass)
    SD  / OD  : different subject / object (no link)
    VR  / VD  : related / different predicate (an antonym counts as VD)
    h         : the HOW patterns of the two ideas are the same (decided by the HOW rules)

Each rule is (rule_id, case, condition, output, example). Outputs use the five relationship types.
"""
from __future__ import annotations

from ..models import Relationship as R

D, G, A, S, X = R.DUPLICATE, R.GENERALISE_DETAIL, R.ALTERNATIVE, R.SIMILAR, R.DISJOINT

WHAT_RULES = [
    # --- WHAT: triple vs single term (Appendix B, block 1)
    ("W01", "T-W", "S1 or O1 linked to W (sameAs, subclass, superclass or similar) and same HOW", G,
     "Window composed of heat-sensitive material (indicates the exit path) / window (shows the exit path)"),
    ("W02", "T-W", "S1 or O1 linked to W and different HOW", A,
     "Window composed of heat-sensitive material (shows person position) / Facade (paints the exit path)"),
    ("W03", "T-W", "no link between S1/O1 and W, same HOW", S,
     "Window composed of heat-sensitive material (indicates the escape route) / Smoke (shows the exit path)"),
    ("W04", "T-W", "no link between S1/O1 and W, different HOW", X,
     "Window composed of heat-sensitive material (sends information to fire department) / Smoke (shows the exit path)"),
    # --- WHAT: triple vs sequence of words (block 2)
    ("W05", "T-SW", "SW linked to S1+O1 and same HOW", S,
     "The building consists of a variable structure (indicates the escape route) / Changeable building structure (shows the exit path)"),
    ("W06", "T-SW", "SW linked to S1+O1 and different HOW", A,
     "The building consists of a variable structure (indicates the escape route) / Changeable building structure (transforms to flying jet)"),
    ("W07", "T-SW", "no link between SW and S1+O1, same HOW", A,
     "The building consists of a variable structure (indicates the escape route) / Flying Drones (shows the exit path)"),
    ("W08", "T-SW", "no link between SW and S1+O1, different HOW", X,
     "The building consists of a variable structure (indicates the escape route) / Non-flammable suit (activates and covers the body)"),
    # --- WHAT: triple vs triple (block 3, rules 1-9; Algorithm 1)
    ("W09", "T-T", "SRS VR ORS and same HOW (rule 1a)", D,
     "Window composed of heat-sensitive material (indicates the exit path) / Window made of heat-sensitive material (shows the exit path)"),
    ("W10", "T-T", "SRS VR ORS and different HOW (rule 1b)", A,
     "Window composed of heat-sensitive material (indicates the exit path) / Window made of heat-sensitive material (sends position info)"),
    ("W11", "T-T", "(SR or SRS) VR (OR or ORS), not all same, and same HOW (rule 2a)", G,
     "Window composed of heat-sensitive material (indicates the exit path) / Architecture element made of TCO (shows the exit path)"),
    ("W12", "T-T", "(SR or SRS) VR (OR or ORS), not all same, and different HOW (rule 2b)", A,
     "Window composed of heat-sensitive material (indicates the position) / Architecture element made of TCO (prints exit path on wall)"),
    ("W13", "T-T", "(SR or SRS) VR OD and same HOW (rule 3a)", A,
     "Window composed of heat-sensitive material (indicates the exit path) / Architecture element made of plants (shows the exit path)"),
    ("W14", "T-T", "(SR or SRS) VR OD and different HOW (rule 3b)", X,
     "Window composed of heat-sensitive material (indicates the exit path) / Architecture element made of plants (sends position information through the smell)"),
    ("W15", "T-T", "(SR or SRS) VD (OR or ORS) and same HOW (rule 4a)", A,
     "The building consists of a variable structure (indicates the exit path) / Architecture element cover-up of TCO (shows the exit path)"),
    ("W16", "T-T", "(SR or SRS) VD (OR or ORS) and different HOW (rule 4b)", X,
     "The building consists of a variable structure (transforms into flying bed) / Architecture element cover-up of TCO (shows the exit path)"),
    ("W17", "T-T", "(SR or SRS) VD OD, same or different HOW (rule 5)", X,
     "The building consists of a variable structure (covers person body) / Architecture element cover-up with inflammable material (packs human)"),
    ("W18", "T-T", "SD VR (OR or ORS) and same HOW (rule 6a)", A,
     "The room consists of a variable structure (capsules human) / Refrigerator made of TCO (packs human)"),
    ("W19", "T-T", "SD VR (OR or ORS) and different HOW (rule 6b)", X,
     "The room consists of a variable structure (turns into a tunnel) / Refrigerator made of TCO (packs human)"),
    ("W20", "T-T", "SD VR OD and different HOW (rule 7a)", X,
     "The room consists of a variable structure (covers person) / Refrigerator made of inflammable material (packs human)"),
    ("W21", "T-T", "SD VR OD and same HOW (rule 7b)", A,
     "The room consists of a variable structure (turns into a tunnel) / Refrigerator made of inflammable material (packs human)"),
    ("W22", "T-T", "SD VD OD and same HOW (rule 8a)", A,
     "The room consists of a variable structure (packs human) / Refrigerator cover-up of inflammable material (packs human)"),
    ("W23", "T-T", "SD VD OD and different HOW (rule 8b)", X,
     "The room consists of a variable structure (turns into a tunnel) / Refrigerator cover-up of inflammable material (packs human)"),
    ("W24", "T-T", "SD VD (OR or ORS) and same HOW (rule 9a)", A,
     "The room consists of inflammable material (packs human) / Refrigerator cover-up of inflammable material (packs human)"),
    ("W25", "T-T", "SD VD (OR or ORS) and different HOW (rule 9b)", X,
     "The room consists of a inflammable material (absorbs fire) / Refrigerator cover-up of inflammable material (packs human)"),
    # --- WHAT: single term vs single term (block 4)
    ("W26", "W-W", "W1 subclass or superclass of W2 and same HOW", G,
     "Window (indicates the escape route) / Structure element (shows the exit path)"),
    ("W27", "W-W", "W1 subclass or superclass of W2 and different HOW", A,
     "Window (indicates the escape route) / Structure element (transforms to a cloud)"),
    ("W28", "W-W", "W1 same as W2 and same HOW", D,
     "Window (indicates the escape route) / Window (shows the exit path)"),
    ("W29", "W-W", "W1 same as W2 and different HOW", A,
     "Window (generates lights) / Window (sends information about the position)"),
    ("W30", "W-W", "W1 similar to W2 and same HOW", A,
     "Window (indicates the exit path) / Facade (shows the exit path)"),
    ("W31", "W-W", "W1 similar to W2 and different HOW", X,
     "Window (shows the exit path) / Facade (sends information about the position)"),
    ("W32", "W-W", "W1 not linked to W2 and same HOW", A,
     "Window (indicates the exit path) / Smoke (shows the exit path)"),
    ("W33", "W-W", "W1 not linked to W2 and different HOW", X,
     "Smoke (shows the exit path) / Window (sends information about the position)"),
    # --- WHAT: single term vs sequence of words (block 5)
    ("W34", "W-SW", "W linked to SW and same HOW", S,
     "Intelligent rescue system (shows the exit path) / Mobile app (indicates the escape route)"),
    ("W35", "W-SW", "W linked to SW and different HOW", X,
     "Intelligent rescue system (paints exit path on wall) / Mobile app (indicates the escape route)"),
    ("W36", "W-SW", "W not linked to SW and same HOW", A,
     "Intelligent rescue system (shows the exit path) / Window (indicates the escape route)"),
    ("W37", "W-SW", "W not linked to SW and different HOW", X,
     "Intelligent rescue system (shows the exit path) / Window (transforms to cloud)"),
    # --- WHAT: sequence of words vs sequence of words (block 6)
    ("W38", "SW-SW", "SW1 linked to SW2 and same HOW", S,
     "Flying robots (move person to outside) / Mobile rescue-drone (guide person to exit path)"),
    ("W39", "SW-SW", "SW1 linked to SW2 and different HOW", X,
     "Flying robots (move person to outside) / Mobile rescue-drone (docks the wall into escape route)"),
    ("W40", "SW-SW", "SW1 not linked to SW2 and same HOW", A,
     "Changeable building structure (docks into escape route) / Mobile rescue-drone (docks the wall into escape route)"),
    ("W41", "SW-SW", "SW1 not linked to SW2 and different HOW", X,
     "Changeable building structure (docks into escape route) / Mobile rescue-drone (move persons outside)"),
]

HOW_RULES = [
    ("H01", "T-T", "SR VR OR -> same HOW", True, "Window indicates people / Facade shows person"),
    ("H02", "T-T", "SR VR OD -> different HOW", False, "Window indicates path of exit / Facade shows person position"),
    ("H03", "T-T", "SR VD OR -> same HOW", True, "Window indicates path of exit / Facade paints path of exit"),
    ("H04", "T-T", "SR VD OD -> different HOW", False, "Window indicates person position / Facade paints path of exit"),
    ("H05", "T-T", "SD VR OR -> same HOW", True, "Window indicates path of exit / smoke shows path of exit"),
    ("H06", "T-T", "SD VR OD -> different HOW", False, "Window indicates position / smoke shows path of exit"),
    ("H07", "T-T", "SD VD OD -> different HOW", False, "net works as slide / Smoke shows the path of exit"),
    ("H08", "T-T", "SD VD OR -> different HOW", False, "structure transforms to fire escape / Smoke shows the path of exit"),
    ("H09", "T-W", "S1 or O1 linked to W -> same HOW, else different", None, "signal is on outside / information"),
    ("H10", "T-SW", "S1 P1 O1 linked to SW -> same HOW, else different", None, "signal is on outside / save navigation to the exit"),
    ("H11", "W-W", "W1 same, similar, subclass or superclass of W2 -> same HOW, else different", None, "exit path / escape route"),
    ("H12", "W-SW", "W linked to SW -> same HOW, else different", None, "position / save navigation to the exit"),
    ("H13", "SW-SW", "SW1 linked to SW2 -> same HOW, else different", None, "sending and receiving info / save navigation to the exit"),
]

RULES = {r[0]: r for r in WHAT_RULES + HOW_RULES}
assert len(WHAT_RULES) == 41 and len(HOW_RULES) == 13


def rule_text(rule_id: str) -> str:
    r = RULES[rule_id]
    return f"{r[0]} [{r[1]}]: {r[2]}"


def as_table() -> list[dict]:
    rows = []
    for r in WHAT_RULES:
        rows.append({"rule_id": r[0], "pattern": "WHAT", "case": r[1], "condition": r[2], "output": r[3].value, "example": r[4]})
    for r in HOW_RULES:
        out = {True: "same HOW", False: "different HOW", None: "same HOW if linked, else different"}[r[3]]
        rows.append({"rule_id": r[0], "pattern": "HOW", "case": r[1], "condition": r[2], "output": out, "example": r[4]})
    return rows
