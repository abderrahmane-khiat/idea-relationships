"""SBERT baseline (sheet 04, columns F-H; Tables 9, 10 and 12 of the revised manuscript).

    python experiments/01_sbert/run_sbert.py                      # input as used for the reported scores
    python experiments/01_sbert/run_sbert.py --input sbert_pairs_input_sheet01.csv

Model sentence-transformers/all-mpnet-base-v2, normalised embeddings, cosine similarity, related if >= 0.75.
Three inputs: the raw idea texts; the 'WHAT HOW' concatenation; the mean of the WHAT-WHAT and HOW-HOW cosines
(the WHAT cosine alone when a HOW is missing). The first run downloads the model (about 420 MB).
Writes outputs/sbert_scores_rerun.csv and compares it with the workbook.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from common import S_BASE, binary, check_numeric, reference, report, sheet  # noqa: E402

MODEL = "sentence-transformers/all-mpnet-base-v2"
THR = 0.75


def main(inp):
    from sentence_transformers import SentenceTransformer
    df = pd.read_csv(HERE / inp, encoding="utf-8").fillna("")
    model = SentenceTransformer(MODEL)

    def cos(a, b):
        ea = model.encode([str(x) for x in a], normalize_embeddings=True, show_progress_bar=False)
        eb = model.encode([str(x) for x in b], normalize_embeddings=True, show_progress_bar=False)
        return (ea * eb).sum(axis=1)

    raw = cos(df.Idea1_Text, df.Idea2_Text)
    concat = cos((df.Idea1_WHAT + " " + df.Idea1_HOW).str.strip(), (df.Idea2_WHAT + " " + df.Idea2_HOW).str.strip())
    what = cos(df.Idea1_WHAT, df.Idea2_WHAT); how = cos(df.Idea1_HOW, df.Idea2_HOW)
    has_how = ((df.Idea1_HOW != "") & (df.Idea2_HOW != "")).values
    mean = what.copy(); mean[has_how] = (what[has_how] + how[has_how]) / 2
    out = pd.DataFrame(dict(Pair_ID=df.Pair_ID, SBERT_raw_text=raw.round(6), SBERT_WHAT_HOW_concat=concat.round(6),
                            SBERT_WHAT_HOW_mean=mean.round(6)))
    (HERE / "outputs").mkdir(exist_ok=True)
    out.to_csv(HERE / "outputs" / "sbert_scores_rerun.csv", index=False)
    print("written outputs/sbert_scores_rerun.csv")

    gold = reference().Related.values.astype(bool)
    for c in ("SBERT_raw_text", "SBERT_WHAT_HOW_concat", "SBERT_WHAT_HOW_mean"):
        for t in (THR, 0.60):
            report(f"{c} >= {t:.2f}", binary(out[c].values >= t, gold))
    base = sheet(S_BASE)
    assert (base.Pair_ID.values == out.Pair_ID.values).all()
    for c in ("SBERT_raw_text", "SBERT_WHAT_HOW_concat", "SBERT_WHAT_HOW_mean"):
        check_numeric(out[c], base[c], c, tol=1e-3)
    print("Small differences (below 1e-3) can come from other torch / sentence-transformers versions.")


if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[args.index("--input") + 1] if "--input" in args else "sbert_pairs_input.csv")
