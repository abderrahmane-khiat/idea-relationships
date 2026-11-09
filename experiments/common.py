"""Shared helpers for the experiment scripts: workbook location, sheet names, metrics, comparison with the workbook."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
WB = ROOT / "data" / "idea_relationships_data.xlsx"

S_IDEAS = "01_Ideas_R2-4"
S_PAIRS = "02_Test_Pairs_R1-1_R1-2_R3-9"
S_POP = "03_Sampling_R3-1"
S_BASE = "04_Baseline_Outputs_R2-4_R3-7"
S_EXT = "13_Extraction_R1-7_R2-5_R3-8"
S_SCREEN = "20_Screening_R1-8"
S_STRAT = "23_Stratified_F_R3-1"
S_ADELIE = "24_ADELIE_Optional_R3-8"

SEED = 2026
CLASSES = ["disjoint", "alternative-solution", "similar", "duplicate"]   # classes with human labels (macro average)
LABELS = CLASSES + ["generalises"]

# Earlier version of the IDEA003 and IDEA020 patterns, used as WHAT+HOW input of the GPT-4o WHAT+HOW runs (R1, R2)
# and of the SBERT WHAT+HOW scores; the 11 pairs concerned are flagged in sheet 04, column P.
EARLIER_PATTERNS = {
    "IDEA003": ("smart fire extinguisher with integrated fire detector", "Shows escape routes and absorbes smoke"),
    "IDEA020": ("Window composed of heat-sensitive material", "indicates the exit path"),
}


def sheet(name, **kw):
    return pd.read_excel(WB, name, **kw)


def norm_label(s) -> str:
    t = str(s).strip().lower().strip(".\"'* ")
    t = t.replace("alternative solution", "alternative-solution").replace("alternative_solution", "alternative-solution")
    t = {"generalise": "generalises", "generalize": "generalises", "generalizes": "generalises",
         "details": "generalises", "generalises/details": "generalises"}.get(t, t)
    return t if t in LABELS else "INVALID"


def reference():
    """Pair_ID, annotator-majority label and binary reference (1 = related) of the 240 test pairs."""
    p = sheet(S_PAIRS)
    p["Human_Majority"] = p.Human_Majority.map(norm_label)
    p["Related"] = (p.Human_Majority != "disjoint").astype(int)
    return p


def binary(pred, gold) -> dict:
    pred = np.asarray(pred, bool); gold = np.asarray(gold, bool)
    tp = int((pred & gold).sum()); fp = int((pred & ~gold).sum()); fn = int((~pred & gold).sum()); tn = int((~pred & ~gold).sum())
    p = tp / (tp + fp) if tp + fp else 0.0; r = tp / (tp + fn) if tp + fn else 0.0
    return dict(TP=tp, FP=fp, FN=fn, TN=tn, Precision=p, Recall=r, F1=2 * p * r / (p + r) if p + r else 0.0,
                Accuracy=(tp + tn) / len(gold))


def f1(pred, gold) -> float:
    return binary(pred, gold)["F1"]


def macro(pred, gold) -> dict:
    ps, rs, fs = [], [], []
    for c in CLASSES:
        tp = sum(a == c and b == c for a, b in zip(pred, gold)); pp = sum(a == c for a in pred); gp = sum(b == c for b in gold)
        p = tp / pp if pp else 0.0; r = tp / gp if gp else 0.0
        ps.append(p); rs.append(r); fs.append(2 * p * r / (p + r) if p + r else 0.0)
    return dict(macro_P=float(np.mean(ps)), macro_R=float(np.mean(rs)), macro_F1=float(np.mean(fs)))


def cohen_kappa(a, b):
    a = list(a); b = list(b); n = len(a); labs = sorted(set(a) | set(b))
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.count(l) / n) * (b.count(l) / n) for l in labs)
    return (po - pe) / (1 - pe) if pe < 1 else 1.0, 1 - po


def cv_threshold(scores, gold, seed=SEED, k=5):
    """Out-of-fold predictions: for each fold, the threshold that maximises F1 on the other folds (ties: lowest)."""
    s = np.asarray(scores, float); g = np.asarray(gold, bool)
    fold = np.random.RandomState(seed).permutation(len(s)) % k; pred = np.zeros(len(s), bool); thr = {}
    for j in range(k):
        tr = fold != j; te = fold == j
        best = max(np.unique(s[tr]), key=lambda th: (f1(s[tr] >= th, g[tr]), -th))
        pred[te] = s[te] >= best; thr[j] = float(best)
    return fold, pred, thr


def report(name, r: dict):
    print(f"{name:45s} TP={r['TP']:3d} FP={r['FP']:3d} FN={r['FN']:3d} TN={r['TN']:3d} "
          f"P={r['Precision']:.3f} R={r['Recall']:.3f} F1={r['F1']:.3f}")


def check_numeric(new, old, what, tol=1e-4):
    d = float(np.nanmax(np.abs(np.asarray(new, float) - np.asarray(old, float))))
    print(f"[{'same' if d <= tol else 'DIFFERENT'}] {what}: max difference to the workbook {d:.2e}")
    return d <= tol


def check_equal(new, old, what):
    new = list(new); old = list(old); n = sum(a != b for a, b in zip(new, old))
    print(f"[{'same' if n == 0 else 'DIFFERENT'}] {what}: {n} of {len(old)} values differ from the workbook")
    return n == 0
