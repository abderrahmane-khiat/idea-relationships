"""Tune the configuration with nested cross-validation (no test pair is used to choose its own settings).

    python scripts/tune.py [--oracle data/oracle_ideas.json] [--repeats 20] [--out results/tuning]

1. Every configuration of the grid below is run once on the 240 pairs (predictions do not depend on training).
2. Repeated stratified 5-fold cross-validation (seed 2026): in each fold, the configuration with the best
   binary F1 on the 4 training folds is selected and applied to the held-out fold. The held-out predictions
   of the 5 folds are pooled into one F1 per repeat. Reported: mean and SD over repeats.
3. The configuration that is best on all 240 pairs is also reported, as an in-sample (optimistic) figure,
   and saved as config/tuned.json (or config/tuned_oracle.json).
"""
import argparse
import itertools
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from idearel import Framework, load_config  # noqa: E402
from idearel.config import copy_config  # noqa: E402
from idearel.evaluation import binary_metrics, load_ideas, load_pairs, multiclass_metrics, run_pairs  # noqa: E402

GRID = {   # first value = default of the paper / package
    "rules.how_same": ["appendix", "object", "any"],
    "thresholds.linguistic": [0.75, 0.6, 0.5],
    "thresholds.content": [0.8, 0.7, 0.6, 0.5],
    "content.sentence_method": ["average", "alignment"],
    "linguistic.lexicon_file": ["config/lexicon.json", ""],
    "implicit_how_subject": [True, False],
    "structure.max_hypernym_depth": [6, 4],
}


GRID_V2 = {
    "rules_version": ["v2"],
    "rules_v2.hier_different": ["disjoint", "similar"],
    "rules_v2.abstain": [True, False],
    "rules_v2.margin": [0.03, 0.05, 0.0],
    "thresholds.linguistic": [0.75, 0.6, 0.5],
    "thresholds.content": [0.8, 0.7, 0.6],
    "content.sentence_method": ["average", "alignment"],
    "linguistic.lexicon_file": ["config/lexicon.json", ""],
}


def set_dotted(cfg, key, value):
    d = cfg
    *path, last = key.split(".")
    for k in path:
        d = d.setdefault(k, {})
    d[last] = value


def f1_of(gold, pred):
    return binary_metrics(gold, pred)["f1"]


def stratified_folds(labels, k, rng):
    idx = np.arange(len(labels))
    folds = [[] for _ in range(k)]
    for cls in (True, False):
        members = idx[np.array(labels) == cls]
        rng.shuffle(members)
        for i, m in enumerate(members):
            folds[i % k].append(m)
    return [np.array(sorted(f)) for f in folds]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--oracle")
    ap.add_argument("--rules", choices=["v1", "v2"], default="v1")
    ap.add_argument("--repeats", type=int, default=20)
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--out", default=str(ROOT / "results" / "tuning"))
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)

    ideas, pairs = load_ideas(), load_pairs()
    gold = [p["Human_Majority"].strip().lower() for p in pairs]
    base = load_config()
    grid = GRID_V2 if a.rules == "v2" else GRID
    keys = list(grid)
    combos = list(itertools.product(*grid.values()))
    preds = []
    for n, values in enumerate(combos, 1):
        cfg = copy_config(base)
        for k, v in zip(keys, values):
            set_dotted(cfg, k, v)
        res = run_pairs(Framework(cfg, a.oracle), pairs, ideas)
        preds.append(["disjoint" if r["Predicted"] == "unknown" else r["Predicted"] for r in res])
        print(f"\r  configuration {n}/{len(combos)}", end="", file=sys.stderr, flush=True)
    print(file=sys.stderr)
    P = np.array(preds)                                   # configs x pairs
    G = np.array(gold)
    related = G != "disjoint"

    def f1_rows(rows):
        g = related[rows]
        p = P[:, rows] != "disjoint"
        tp = (p & g).sum(1); fp = (p & ~g).sum(1); fn = (~p & g).sum(1)
        return np.where(2 * tp + fp + fn > 0, 2 * tp / np.maximum(2 * tp + fp + fn, 1), 0.0)

    rng = np.random.default_rng(2026)
    cv_f1, cv_macro, chosen = [], [], Counter()
    for _ in range(a.repeats):
        pooled = np.empty(len(G), dtype=object)
        for test in stratified_folds(list(related), a.folds, rng):
            train = np.setdiff1d(np.arange(len(G)), test)
            best = int(np.argmax(f1_rows(train)))        # ties -> first = closest to the default
            chosen[best] += 1
            pooled[test] = P[best, test]
        cv_f1.append(f1_of(list(G), list(pooled)))
        cv_macro.append(multiclass_metrics(list(G), list(pooled))["macro"]["f1"])

    all_f1 = f1_rows(np.arange(len(G)))
    best_all = int(np.argmax(all_f1))
    describe = lambda i: dict(zip(keys, combos[i]))
    default_idx = 0
    summary = {
        "elements": "oracle (" + a.oracle + ")" if a.oracle else "extracted (" + base["extractor"] + ")",
        "n_configurations": len(combos),
        "default_configuration": {"config": describe(default_idx),
                                  **binary_metrics(list(G), list(P[default_idx])),
                                  "macro_f1": multiclass_metrics(list(G), list(P[default_idx]))["macro"]["f1"]},
        "nested_cv": {"folds": a.folds, "repeats": a.repeats, "seed": 2026,
                      "binary_f1_mean": float(np.mean(cv_f1)), "binary_f1_sd": float(np.std(cv_f1, ddof=1)),
                      "macro_f1_mean": float(np.mean(cv_macro)), "macro_f1_sd": float(np.std(cv_macro, ddof=1)),
                      "most_chosen": [{"config": describe(i), "times": c} for i, c in chosen.most_common(3)]},
        "best_in_sample": {"config": describe(best_all), **binary_metrics(list(G), list(P[best_all])),
                           "macro_f1": multiclass_metrics(list(G), list(P[best_all]))["macro"]["f1"],
                           "note": "chosen and scored on the same 240 pairs: optimistic"},
    }
    tag = ("oracle" if a.oracle else "extracted") + ("_v2" if a.rules == "v2" else "")
    (out / f"tuning_{tag}.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    cfg = copy_config(base)
    for k, v in describe(best_all).items():
        set_dotted(cfg, k, v)
    cfg["_comment"] = f"Configuration selected by scripts/tune.py ({tag} elements); see results/tuning/tuning_{tag}.json"
    name = f"tuned_{tag}.json".replace("tuned_extracted", "tuned")
    (ROOT / "config" / name).write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
