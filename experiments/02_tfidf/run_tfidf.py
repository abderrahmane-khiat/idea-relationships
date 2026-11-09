"""TF-IDF baseline (sheet 04, columns I, S, T; Baseline 5 and Tables 9, 10, 12 of the revised manuscript).

    python experiments/02_tfidf/run_tfidf.py

scikit-learn TfidfVectorizer (lowercase, English stop words, sublinear tf) fitted on the 52 idea texts of sheet 01;
cosine similarity of the two raw idea texts. Related if cosine >= threshold:
  - threshold chosen by 5-fold cross-validation (seed 2026): for each fold, the threshold with the best F1 on the
    other four folds (out-of-fold predictions; the fair comparison, F1 0.423);
  - threshold 0.20 chosen on the test labels (optimistic upper bound, F1 0.528);
  - full sweep 0.05-0.95 (Table 12).
Writes outputs/tfidf_scores_rerun.csv and outputs/tfidf_sweep_rerun.csv and compares them with the workbook.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from common import S_BASE, S_IDEAS, S_PAIRS, binary, check_equal, check_numeric, cv_threshold, reference, report, sheet  # noqa: E402


def main():
    ideas = sheet(S_IDEAS); pairs = sheet(S_PAIRS)
    vec = TfidfVectorizer(lowercase=True, stop_words="english", sublinear_tf=True).fit(ideas.Idea_Text.tolist())
    a = vec.transform(pairs.Idea1_Text); b = vec.transform(pairs.Idea2_Text)
    cosine = np.asarray(a.multiply(b).sum(1)).ravel()

    gold = reference().Related.values.astype(bool)
    fold, pred, thr = cv_threshold(cosine, gold)
    out = pd.DataFrame(dict(Pair_ID=pairs.Pair_ID, TFIDF_cosine=cosine.round(6), TFIDF_CV_Fold=fold,
                            TFIDF_CV_Related=pred.astype(int), TFIDF_tuned_020_Related=(cosine >= 0.20).astype(int)))
    (HERE / "outputs").mkdir(exist_ok=True)
    out.to_csv(HERE / "outputs" / "tfidf_scores_rerun.csv", index=False)
    sweep = pd.DataFrame([dict(Threshold=t, **binary(cosine >= t, gold)) for t in np.round(np.arange(0.05, 0.951, 0.05), 2)])
    sweep.round(4).to_csv(HERE / "outputs" / "tfidf_sweep_rerun.csv", index=False)
    print("written outputs/tfidf_scores_rerun.csv, outputs/tfidf_sweep_rerun.csv")

    print("thresholds chosen per fold:", {k: round(v, 4) for k, v in thr.items()})
    report("TF-IDF, 5-fold CV threshold", binary(pred, gold))
    report("TF-IDF, threshold 0.20 (tuned on test)", binary(cosine >= 0.20, gold))
    best = sweep.loc[sweep.F1.idxmax()]
    print(f"best threshold of the sweep: {best.Threshold:.2f} (F1 {best.F1:.3f})")

    base = sheet(S_BASE)
    check_numeric(cosine, base.TFIDF_cosine, "TFIDF_cosine")
    check_equal(fold, base.TFIDF_CV_Fold, "TFIDF_CV_Fold")
    check_equal(pred.astype(int), base.TFIDF_CV_Related, "TFIDF_CV_Related")


if __name__ == "__main__":
    main()
