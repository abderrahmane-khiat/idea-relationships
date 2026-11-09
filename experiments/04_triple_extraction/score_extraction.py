"""Triple extraction: Stanford OpenIE vs GPT-4o on the 70 WHAT/HOW phrases of Study 4 (sheet 13; Table 15 triple rows, Section 9.5).

    python experiments/04_triple_extraction/score_extraction.py                       # reported judgements
    python experiments/04_triple_extraction/score_extraction.py my_judged_file.csv    # your own judgements

Precision = correct / extracted triples; recall = correct / expected triples (Triple_Expected = Y, from the expert
flags). Lenient judging accepts a relative pronoun ('that') as subject, as in the expert validation of OpenIE;
strict judging counts it as Not Correct.
To judge a new extractor: copy outputs/openie_vs_gpt4o_judged.csv, replace GPT4o_S/P/O with the new triples
(NONE for no element), fill Judgement_Lenient and Judgement_Strict (Correct / Not Correct) for every extracted
triple, and pass the file to this script.
"""
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent


def score(e):
    rows = []
    for pat in ("WHAT", "HOW"):
        d = e[e.Pattern == pat]; exp = int((d.Triple_Expected == "Y").sum())
        ext_o = int((d.OpenIE_Type == "triple").sum())
        cor_o = int(((d.OpenIE_Type == "triple") & (d.OpenIE_Judgement == "Correct")).sum())
        ext_g = int((d[["GPT4o_S", "GPT4o_P", "GPT4o_O"]].astype(str) != "NONE").all(axis=1).sum())
        for name, ext, cor in (("Stanford OpenIE (CoreNLP 4.5.5)", ext_o, cor_o),
                               ("GPT-4o, lenient judging", ext_g, int((d.Judgement_Lenient == "Correct").sum())),
                               ("GPT-4o, strict judging", ext_g, int((d.Judgement_Strict == "Correct").sum()))):
            p = cor / ext if ext else 0.0; r = cor / exp if exp else 0.0
            rows.append(dict(Pattern=pat, Extractor=name, Extracted=ext, Correct=cor, Expected=exp,
                             Precision=p, Recall=r, F1=2 * p * r / (p + r) if p + r else 0.0))
    return pd.DataFrame(rows)


if __name__ == "__main__":
    f = sys.argv[1] if len(sys.argv) > 1 else HERE / "outputs" / "openie_vs_gpt4o_judged.csv"
    res = score(pd.read_csv(f).fillna(""))
    print(res.round(3).to_string(index=False))
    if len(sys.argv) == 1:                      # reported judgements: compare with the summary of sheet 13
        sys.path.insert(0, str(HERE.parent))
        from common import S_EXT, check_numeric, sheet
        w = sheet(S_EXT, header=2, usecols="S:Z").dropna(subset=["Extracted"]).head(6).rename(columns={"Correct.1": "Correct"})
        check_numeric(res[["Extracted", "Correct", "Expected", "Precision", "Recall", "F1"]].values,
                      w[["Extracted", "Correct", "Expected", "Precision", "Recall", "F1"]].astype(float).values, "sheet 13 summary")
