"""Evaluation utilities: the same metrics as the paper (Tables 5-8, 14) computed on the released data.

Reference label = Human_Majority (Phase-2 majority of annotators A, B, C).
  Task 1 (binary):    related (any non-disjoint type) vs disjoint.
  Task 2 (five-way):  confusion matrix and macro P/R/F1 over duplicate, alternative-solution,
                      similar and disjoint (generalise/detail has no reference instance in the 240 pairs).
"""
from __future__ import annotations

import csv
import itertools
import json
from collections import Counter
from pathlib import Path

import numpy as np

from .config import ROOT, copy_config
from .models import Idea, Relationship
from .pipeline import Framework

DATA = ROOT / "data"
CLASSES = ["duplicate", "generalise/detail", "alternative-solution", "similar", "disjoint"]
MACRO_CLASSES = ["duplicate", "alternative-solution", "similar", "disjoint"]
ALIASES = {"generalises": "generalise/detail", "generalise": "generalise/detail", "detail": "generalise/detail",
           "alternative": "alternative-solution", "alternative solution": "alternative-solution"}


def norm_label(x: str) -> str:
    x = (x or "").strip().lower()
    return ALIASES.get(x, x)


# ------------------------------------------------------------------ data
def read_csv(path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_ideas(path=DATA / "ideas.csv") -> dict[str, Idea]:
    out = {}
    for r in read_csv(path):
        out[r["Idea_ID"]] = Idea(id=r["Idea_ID"], text=r.get("Idea_Text", ""), what=r.get("WHAT", ""),
                                 how=r.get("HOW", ""), when=r.get("WHEN", ""))
    return out


def load_pairs(path=DATA / "pairs.csv") -> list[dict]:
    return read_csv(path)


# ------------------------------------------------------------------ metrics
def prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return p, r, f


def binary_metrics(gold: list[str], pred: list[str]) -> dict:
    g = [x != "disjoint" for x in gold]
    p = [x != "disjoint" for x in pred]
    tp = sum(a and b for a, b in zip(g, p)); fp = sum((not a) and b for a, b in zip(g, p))
    fn = sum(a and (not b) for a, b in zip(g, p)); tn = sum((not a) and (not b) for a, b in zip(g, p))
    P, R, F = prf(tp, fp, fn)
    return {"TP": tp, "FP": fp, "FN": fn, "TN": tn, "precision": P, "recall": R, "f1": F, "accuracy": (tp + tn) / len(g)}


def multiclass_metrics(gold: list[str], pred: list[str], classes=MACRO_CLASSES) -> dict:
    labels = CLASSES
    cm = {g: Counter() for g in labels}
    for a, b in zip(gold, pred):
        cm.setdefault(a, Counter())[b] += 1
    per = {}
    for c in classes:
        tp = cm.get(c, Counter())[c]
        fp = sum(cm[g][c] for g in cm if g != c)
        fn = sum(v for k, v in cm.get(c, Counter()).items() if k != c)
        P, R, F = prf(tp, fp, fn)
        per[c] = {"precision": P, "recall": R, "f1": F, "support": sum(cm.get(c, Counter()).values())}
    macro = {k: float(np.mean([per[c][k] for c in classes])) for k in ("precision", "recall", "f1")}
    return {"confusion": {g: dict(cm[g]) for g in labels if g in cm}, "per_class": per, "macro": macro,
            "accuracy": sum(a == b for a, b in zip(gold, pred)) / len(gold)}


def cohen_kappa(a: list[str], b: list[str]) -> float:
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n * n)
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


def bootstrap_f1(gold, pred, n=2000, seed=2026) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    g = np.array([x != "disjoint" for x in gold]); p = np.array([x != "disjoint" for x in pred])
    vals = []
    for _ in range(n):
        i = rng.integers(0, len(g), len(g))
        tp = np.sum(g[i] & p[i]); fp = np.sum(~g[i] & p[i]); fn = np.sum(g[i] & ~p[i])
        vals.append(prf(tp, fp, fn)[2])
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


# ------------------------------------------------------------------ experiments
def run_pairs(fw: Framework, pairs: list[dict], ideas: dict[str, Idea], progress=None) -> list[dict]:
    out = []
    for i, p in enumerate(pairs):
        d = fw.compare(ideas[p["Idea1_ID"]], ideas[p["Idea2_ID"]])
        out.append({"Pair_ID": p["Pair_ID"], "Idea1_ID": p["Idea1_ID"], "Idea2_ID": p["Idea2_ID"],
                    "Human_Majority": norm_label(p.get("Human_Majority", "")),
                    "Original_System_Label": norm_label(p.get("System_Label", "")),
                    "Predicted": d.relationship.value, "Rule": d.rule_id, "HOW_rule": d.how_rule_id,
                    "HOW_same": d.how_same, "Case": d.codes.get("case", ""), "Direction": d.direction,
                    "Codes": json.dumps({k: v for k, v in d.codes.items() if k != "case"}),
                    "Matchers_used": ";".join(sorted({l["matcher"] for l in d.links if l["matcher"]}))})
        if progress:
            progress(i + 1, len(pairs))
    return out


def selective(gold: list[str], pred: list[str]) -> dict:
    """Rules v2: coverage and metrics on the pairs that were decided (unknown = abstained)."""
    keep = [i for i, p in enumerate(pred) if p != "unknown"]
    out = {"coverage": len(keep) / len(pred), "n_unknown": len(pred) - len(keep),
           "unknown_among_related": sum(1 for g, p in zip(gold, pred) if p == "unknown" and g != "disjoint")}
    if keep:
        out["binary_on_decided"] = binary_metrics([gold[i] for i in keep], [pred[i] for i in keep])
    return out


def summarise(results: list[dict]) -> dict:
    gold = [r["Human_Majority"] for r in results]
    raw = [r["Predicted"] for r in results]
    pred = ["disjoint" if p == "unknown" else p for p in raw]      # unknown counted as not related
    orig = [r["Original_System_Label"] for r in results]
    s = {"n_pairs": len(results), "binary": binary_metrics(gold, pred), "five_way": multiclass_metrics(gold, pred),
         "binary_f1_95ci": bootstrap_f1(gold, pred),
         "agreement_with_original_system": {"accuracy": sum(a == b for a, b in zip(orig, pred)) / len(pred),
                                            "cohen_kappa": cohen_kappa(orig, pred)} if any(orig) else None,
         "original_system_binary": binary_metrics(gold, orig) if any(orig) else None,
         "rule_usage": dict(Counter(r["Rule"] for r in results).most_common()),
         "label_counts": dict(Counter(raw))}
    if "unknown" in raw:
        s["abstention"] = selective(gold, raw)
    return s


def ablation(cfg: dict, pairs, ideas) -> list[dict]:
    """Every non-empty subset of matchers (15 runs), in the configured order."""
    rows = []
    order = cfg["cascade"]["order"]
    for k in range(1, len(order) + 1):
        for subset in itertools.combinations(order, k):
            c = copy_config(cfg); c["cascade"]["enabled"] = list(subset)
            res = run_pairs(Framework(c), pairs, ideas)
            b = summarise(res)["binary"]
            rows.append({"matchers": "+".join(subset), **{k2: round(v, 3) if isinstance(v, float) else v for k2, v in b.items()}})
    return rows


def cascade_orders(cfg: dict, pairs, ideas) -> list[dict]:
    rows = []
    for order in itertools.permutations(cfg["cascade"]["enabled"]):
        c = copy_config(cfg); c["cascade"]["order"] = list(order)
        b = summarise(run_pairs(Framework(c), pairs, ideas))["binary"]
        rows.append({"order": " > ".join(order), **{k: round(v, 3) if isinstance(v, float) else v for k, v in b.items()}})
    return rows


def calibrate(cfg: dict, path=DATA / "term_pairs.csv", grid=None) -> dict:
    """Score the 172 term pairs with each matcher of THIS implementation and sweep its threshold.

    Returns, per matcher, F1 on the train split and the held-out split for every threshold.
    """
    from .matching.matchers import ContentMatcher, LinguisticMatcher, TerminologyMatcher
    grid = grid or [round(x, 2) for x in np.arange(0.50, 0.951, 0.05)]
    pos_of = {"NounMatching": "n", "VerbMatching": "v", "SentenceMatching": "s"}
    rows = read_csv(path)
    matchers = {"linguistic": LinguisticMatcher(cfg), "content": ContentMatcher(cfg), "terminology": TerminologyMatcher(cfg)}
    scores = {m: [] for m in matchers}
    for r in rows:
        a, b = r["Term_Pair_Text"].split("-", 1)
        pos = pos_of.get(r["Source"], "n")
        for name, m in matchers.items():
            if name == "linguistic" and pos == "s":
                scores[name].append(None); continue
            call = m.match(a.strip(), b.strip(), pos)
            scores[name].append(call.score if call.score is not None else 0.0)
    out = {"n_pairs": len(rows), "grid": grid, "matchers": {}, "scores": []}
    for name in matchers:
        res = []
        for t in grid:
            entry = {"threshold": t}
            for split in ("train", "test"):
                g, p = [], []
                for r, s in zip(rows, scores[name]):
                    if r["Split"] != split or s is None:
                        continue
                    g.append(r["Gold_Label"] == "positive"); p.append(s >= t)
                tp = sum(x and y for x, y in zip(g, p)); fp = sum((not x) and y for x, y in zip(g, p))
                fn = sum(x and (not y) for x, y in zip(g, p))
                entry[f"f1_{split}"] = round(prf(tp, fp, fn)[2], 3)
            res.append(entry)
        out["matchers"][name] = res
    for r, *s in zip(rows, *[scores[m] for m in matchers]):
        out["scores"].append({"Term_Pair_ID": r["Term_Pair_ID"], "pair": r["Term_Pair_Text"], "gold": r["Gold_Label"],
                              **{m: v for m, v in zip(matchers, s)}})
    return out


def write_rows(path, rows: list[dict]):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
