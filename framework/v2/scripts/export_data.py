"""Export the CSV inputs of the framework from the release workbook (../../data/idea_relationships_data.xlsx).

    python scripts/export_data.py

Writes data/ideas.csv, data/pairs.csv, data/term_pairs.csv and data/oracle_study4.json.
"""
import csv
import json
import sys
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def rows(ws):
    it = ws.iter_rows(values_only=True)
    head = [h for h in next(it)]
    for r in it:
        if r[0] is None:
            continue
        yield {h: v for h, v in zip(head, r) if h}


def write(path, records, fields):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in records:
            w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in fields})
    print(f"wrote {path.relative_to(ROOT)} ({len(records)} rows)")


def main(xlsx=ROOT.parents[1] / "data" / "idea_relationships_data.xlsx"):
    wb = openpyxl.load_workbook(xlsx, data_only=True)
    sheet = lambda prefix: wb[next(n for n in wb.sheetnames if n.startswith(prefix))]

    ideas = list(rows(sheet("01_")))
    write(DATA / "ideas.csv", ideas, ["Idea_ID", "Idea_Text", "WHAT", "HOW", "WHEN"])

    pairs = list(rows(sheet("02_")))
    write(DATA / "pairs.csv", pairs, ["Pair_ID", "Idea1_ID", "Idea2_ID", "Stratum", "Annotator_A", "Annotator_B",
                                      "Annotator_C", "Human_Majority", "Gold_NonDisjoint", "System_Label", "RuleID"])

    # one row per term pair with the three matcher scores (Table 14 calibration data)
    tp = {}
    for r in rows(sheet("10_")):
        g = r["Term_Pair_Group"]
        d = tp.setdefault(g, {"Term_Pair_ID": g, "Term_Pair_Text": r["Term_Pair_Text"], "Gold_Label": r["Gold_Label"],
                              "Split": r["Split"], "Study": r["Study"], "Source": r["Term_Type_Source"]})
        d[f"Original_{r['Matcher']}"] = r["Raw_Score"]
    write(DATA / "term_pairs.csv", list(tp.values()),
          ["Term_Pair_ID", "Term_Pair_Text", "Gold_Label", "Split", "Study", "Source",
           "Original_Linguistic", "Original_Content", "Original_Terminology"])

    # oracle example: the expert-validated elements of the Study 4 ideas (sheet 13)
    oracle = {}
    for r in rows(sheet("13_")):
        if not r.get("Idea_ID") or not r.get("Pattern"):
            continue
        if r.get("Triple_Expected") == "Y" and r.get("OpenIE_Judgement") == "Correct":
            el = {"type": "triple", "subject": r["OpenIE_S"], "predicate": r["OpenIE_P"], "object": r["OpenIE_O"]}
        elif r.get("Triple_Expected") == "Y":
            continue                       # expected triple not validated: left to the extractor
        else:
            n = len(str(r["Text"]).split())
            el = {"type": "single_term" if n <= 3 else "sequence_of_words", "text": r["Text"]}
        oracle.setdefault(r["Idea_ID"], {})[r["Pattern"]] = el
    (DATA / "oracle_study4.json").write_text(json.dumps(oracle, indent=2), encoding="utf-8")
    print(f"wrote data/oracle_study4.json ({len(oracle)} ideas)")


if __name__ == "__main__":
    main(*sys.argv[1:])
