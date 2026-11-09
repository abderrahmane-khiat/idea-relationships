"""Build the input files of the experiments from the data workbook.

    python experiments/build_inputs.py            # the inputs exactly as they were used for the reported runs
    python experiments/build_inputs.py --sheet01  # the same inputs with the IDEA003/IDEA020 patterns of sheet 01

The GPT-4o WHAT+HOW runs (R1, R2) and the SBERT WHAT+HOW scores used an earlier version of the IDEA003 and IDEA020
patterns (11 pairs, flagged in sheet 04, column P). The default reproduces those inputs; --sheet01 writes
*_sheet01.csv files with the patterns of sheet 01. The raw-text inputs and the definitions run are not affected.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import EARLIER_PATTERNS, S_EXT, S_IDEAS, S_PAIRS, sheet  # noqa: E402

HERE = Path(__file__).resolve().parent


def fmt(what, how):
    """'WHAT. HOW' string given to GPT-4o in the WHAT+HOW condition."""
    return ". ".join(t.strip().rstrip(".") for t in (what, how) if str(t).strip())


def main(sheet01=False):
    ideas = sheet(S_IDEAS).fillna("").set_index("Idea_ID")
    pairs = sheet(S_PAIRS)
    pat_now = {i: (r.WHAT.strip(), r.HOW.strip()) for i, r in ideas.iterrows()}
    pat_run = dict(pat_now)
    if not sheet01:
        pat_run.update(EARLIER_PATTERNS)
    suf = "_sheet01" if sheet01 else ""

    rows = []
    for r in pairs.itertuples():
        (w1, h1), (w2, h2) = pat_run[r.Idea1_ID], pat_run[r.Idea2_ID]
        rows.append(dict(Pair_ID=r.Pair_ID, Idea1_ID=r.Idea1_ID, Idea2_ID=r.Idea2_ID, Idea1_Text=r.Idea1_Text.strip(),
                         Idea2_Text=r.Idea2_Text.strip(), Idea1_WHAT=w1, Idea1_HOW=h1, Idea2_WHAT=w2, Idea2_HOW=h2))
    sb = pd.DataFrame(rows)
    out = {}
    out[HERE / "01_sbert" / f"sbert_pairs_input{suf}.csv"] = sb
    llm = HERE / "03_llm_pair_classification" / "inputs"
    out[llm / f"what_how_240{'_sheet01' if sheet01 else '_as_run'}.csv"] = pd.DataFrame(
        dict(Pair_ID=sb.Pair_ID, Idea1=[fmt(a, b) for a, b in zip(sb.Idea1_WHAT, sb.Idea1_HOW)],
             Idea2=[fmt(a, b) for a, b in zip(sb.Idea2_WHAT, sb.Idea2_HOW)]))
    if not sheet01:
        out[llm / "raw_text_240.csv"] = pd.DataFrame(dict(Pair_ID=sb.Pair_ID, Idea1=sb.Idea1_Text, Idea2=sb.Idea2_Text))
        d = pd.DataFrame([dict(Pair_ID=r.Pair_ID, Idea1_WHAT=pat_now[r.Idea1_ID][0], Idea1_HOW=pat_now[r.Idea1_ID][1],
                               Idea2_WHAT=pat_now[r.Idea2_ID][0], Idea2_HOW=pat_now[r.Idea2_ID][1]) for r in pairs.itertuples()])
        out[llm / "what_how_240_definitions.csv"] = d
        e = sheet(S_EXT, usecols="A:D").dropna(subset=["Item"])
        out[HERE / "04_triple_extraction" / "patterns_70.csv"] = e[["Item", "Idea_ID", "Pattern", "Text"]]
    for path, df in out.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(path, index=False, encoding="utf-8")
        print(f"written {path.relative_to(HERE.parent)} ({len(df)} rows)")


if __name__ == "__main__":
    main(sheet01="--sheet01" in sys.argv)
