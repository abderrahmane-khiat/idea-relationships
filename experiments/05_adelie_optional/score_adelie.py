"""Optional check for Reviewer 3, comment 8 (sheet 24; response letter only, not in the manuscript tables).

    python experiments/05_adelie_optional/score_adelie.py

Relatedness from ADELIE triples: pair score = best word overlap (Jaccard, English stop words removed, words of
two letters or more) between a triple of idea 1 and a triple of idea 2; pairs with an idea without triples are
not scored. Related if score >= threshold, threshold chosen by 5-fold cross-validation (seed 2026).
Writes outputs/adelie_pair_scores_rerun.csv and compares it with the workbook.
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS as SW

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from common import binary, check_equal, check_numeric, cv_threshold, reference, report  # noqa: E402


def tok(t):
    return {w for w in re.findall(r"[a-z]+", " ".join(str(t.get(k, "")) for k in ("subject", "predicate", "object")).lower())
            if w not in SW and len(w) > 1}


def main():
    a = pd.read_csv(HERE / "outputs" / "adelie_triples.csv").fillna("")
    T = {r.Idea_ID: (json.loads(r.ADELIE_Triples_JSON) if r.ADELIE_Triples_JSON else []) for r in a.itertuples()}

    def score(i, j):
        if not T.get(i) or not T.get(j):
            return np.nan
        return max((len(tok(x) & tok(y)) / len(tok(x) | tok(y)) for x in T[i] for y in T[j] if tok(x) | tok(y)), default=0.0)

    ref = reference()
    s = np.array([score(r.Idea1_ID, r.Idea2_ID) for r in ref.itertuples()])
    ok = ~np.isnan(s); g = ref.Related.values.astype(bool); ours = (ref.System_Label.str.strip().str.lower() != "disjoint").values
    fold, pred, thr = cv_threshold(s[ok], g[ok])
    out = pd.DataFrame(dict(Pair_ID=ref.Pair_ID, Idea1_ID=ref.Idea1_ID, Idea2_ID=ref.Idea2_ID, ADELIE_Alignment=np.round(s, 4)))
    out["Fold"] = pd.array([pd.NA] * len(out), dtype="Int64"); out["ADELIE_CV_Related"] = pd.array([pd.NA] * len(out), dtype="Int64")
    out.loc[ok, "Fold"] = fold; out.loc[ok, "ADELIE_CV_Related"] = pred.astype(int)
    out.to_csv(HERE / "outputs" / "adelie_pair_scores_rerun.csv", index=False)
    print(f"scored pairs: {ok.sum()} of {len(ref)}; ideas with triples: {sum(bool(v) for v in T.values())} of {len(T)}; "
          f"triples: {sum(len(v) for v in T.values())}")
    report("ADELIE triples, 5-fold CV threshold", binary(pred, g[ok]))
    report("Our approach, same pairs", binary(ours[ok], g[ok]))
    best = max(np.unique(s[ok]), key=lambda t: (binary(s[ok] >= t, g[ok])["F1"], -t))
    print(f"ADELIE, threshold chosen on the test labels (optimistic): {best:.3f}, F1 {binary(s[ok] >= best, g[ok])['F1']:.3f}")
    old = pd.read_csv(HERE / "outputs" / "adelie_pair_scores.csv")
    check_numeric(np.nan_to_num(s, nan=-1), old.ADELIE_Alignment.fillna(-1), "ADELIE_Alignment")
    check_equal(out.Fold.fillna(-1).astype(int), old.Fold.fillna(-1).astype(int), "Fold")
    check_equal(out.ADELIE_CV_Related.fillna(-1).astype(int), old.ADELIE_CV_Related.fillna(-1).astype(int), "ADELIE_CV_Related")
    print("The paired-bootstrap difference (ours - ADELIE) is computed by evaluate.py.")


if __name__ == "__main__":
    main()
