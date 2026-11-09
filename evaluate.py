"""
evaluate.py - recomputes every reported number of the revised manuscript
"Interpretable Detection of Multidimensional Relationships between Ideas in Crowd Ideation Platforms"
from the release workbook (idea_relationships_data.xlsx).

Usage:   python evaluate.py [data/idea_relationships_data.xlsx]
Needs:   pandas, numpy, scipy, openpyxl, scikit-learn (for the TF-IDF and ADELIE checks)
Output:  printed tables and evaluate_output.csv (one row per metric)

Prints, with the table numbers of the revised manuscript: Tables 5 and 10 (Task 1), 6 and 7 (confusion matrix,
per-class metrics), 8 (rule coverage), 9 (counts per method), 11 (Task 2 macro), 12 (threshold sweep),
13 (cross-tabulation with Dandelion), 15 (triple rows), 16-18 (standalone matchers), 19 (calibration),
20 (matcher ablation), 21 (cascade orders) and 23 (upper bound); the significance tests of Section 7.4;
annotator agreement; the stratified estimate (Section 6.5); the LLM error analysis (Section 7.5); the candidate
screening (Section 9.6); and the optional ADELIE check of the response letter.

Only raw data columns are read (labels, scores, inputs). Formula columns of the workbook are
not used, so this script is an independent check of the formula-based result sheets.
"""
import sys
import itertools

import numpy as np
import pandas as pd
from scipy.stats import binomtest, chi2

# ---------------------------------------------------------------- sheet names
S_IDEAS = "01_Ideas_R2-4"
S_PAIRS = "02_Test_Pairs_R1-1_R1-2_R3-9"
S_POP = "03_Sampling_R3-1"
S_BASE = "04_Baseline_Outputs_R2-4_R3-7"
S_CAL = "10_Calibration_Data_R1-5_R3-2"
S_EXT = "13_Extraction_R1-7_R2-5_R3-8"
S_GEN = "15_Generalise_Check_R1-3_R1-9"

CLASSES = ["disjoint", "alternative-solution", "similar", "duplicate"]   # scored classes
LABELS5 = CLASSES + ["generalises"]
BOOT_B, BOOT_SEED = 10000, 2026
THR = {"Linguistic": 0.75, "Content": 0.80, "Terminology": 0.85}


def norm_label(s):
    t = str(s).strip().lower().replace("alternative solution", "alternative-solution")
    return {"generalise": "generalises", "generalised": "generalises"}.get(t, t)


# ---------------------------------------------------------------- metrics
def binary(pred, gold):
    pred = np.asarray(pred, bool); gold = np.asarray(gold, bool)
    tp = int((pred & gold).sum()); fp = int((pred & ~gold).sum())
    fn = int((~pred & gold).sum()); tn = int((~pred & ~gold).sum())
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return dict(TP=tp, FP=fp, FN=fn, TN=tn, Precision=p, Recall=r, F1=f, Accuracy=(tp + tn) / len(pred),
                Predicted_related=int(pred.sum()))


def f1(pred, gold):
    tp = (pred & gold).sum(); fp = (pred & ~gold).sum(); fn = (~pred & gold).sum()
    return 2 * tp / (2 * tp + fp + fn) if tp else 0.0


def macro(pred, gold):
    rows = []
    for c in CLASSES:
        tp = sum(a == c and b == c for a, b in zip(pred, gold))
        pp = sum(a == c for a in pred); gp = sum(b == c for b in gold)
        p = tp / pp if pp else 0.0; r = tp / gp if gp else 0.0
        rows.append((c, gp, pp, tp, p, r, 2 * p * r / (p + r) if p + r else 0.0))
    m = [float(np.mean([x[i] for x in rows])) for i in (4, 5, 6)]
    return rows, dict(macro_P=m[0], macro_R=m[1], macro_F1=m[2])


def cohen_kappa(a, b):
    a = list(a); b = list(b); n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.count(l) / n) * (b.count(l) / n) for l in set(a) | set(b))
    return (po - pe) / (1 - pe), 1 - po


def fleiss_kripp(label_matrix):
    cats = sorted(set(np.ravel(label_matrix)))
    M = np.array([[list(row).count(c) for c in cats] for row in label_matrix], float)
    n, k = M.shape[0], M.sum(1)[0]
    pbar = ((M * (M - 1)).sum(1) / (k * (k - 1))).mean()
    pj = M.sum(0) / (n * k); pe = (pj ** 2).sum()
    fleiss = (pbar - pe) / (1 - pe)
    N = n * k
    do = (k * k - (M ** 2).sum(1)).sum() / ((k - 1) * N)
    de = (N * N - (M.sum(0) ** 2).sum()) / (N * (N - 1))
    return fleiss, 1 - do / de, float((M.max(1) == k).mean())


def boot_f1_diff(sysp, basep, gold, idx):
    d = np.array([f1(sysp[i], gold[i]) - f1(basep[i], gold[i]) for i in idx])
    return f1(sysp, gold) - f1(basep, gold), np.percentile(d, 2.5), np.percentile(d, 97.5)


def mcnemar_related(sysp, basep, gold):
    b = int((sysp[gold] & ~basep[gold]).sum()); c = int((~sysp[gold] & basep[gold]).sum())
    return b, c, (binomtest(b, b + c, 0.5).pvalue if b + c else 1.0)


def mcnemar_accuracy(sysp, basep, gold):
    s = sysp == gold; o = basep == gold
    b = int((s & ~o).sum()); c = int((~s & o).sum())
    x2 = (abs(b - c) - 1) ** 2 / (b + c) if b + c else 0.0
    return b, c, x2, 1 - chi2.cdf(x2, 1)


# ---------------------------------------------------------------- loading
def load(wb):
    pairs = pd.read_excel(wb, S_PAIRS)
    base = pd.read_excel(wb, S_BASE)
    assert (pairs.Pair_ID.values == base.Pair_ID.values).all()
    for c in ["Annotator_A", "Annotator_B", "Annotator_C", "Human_Majority", "System_Label"]:
        pairs[c] = pairs[c].map(norm_label)
    for c in ["GPT4o_raw_R1", "GPT4o_raw_R2", "GPT4o_WHATHOW_R1", "GPT4o_WHATHOW_R2", "Claude_Sonnet55", "Gemini25Flash",
              "GPT4o_WHATHOW_def_R1", "GPT4o_WHATHOW_def_R2"]:
        base[c] = base[c].map(norm_label)
    return pairs, base


def tfidf_cv(base, gold):
    """TF-IDF with a threshold chosen by 5-fold cross-validation (out-of-fold predictions, seed 2026)."""
    s = base.TFIDF_cosine.astype(float).values
    rng = np.random.RandomState(BOOT_SEED); fold = rng.permutation(len(s)) % 5; pred = np.zeros(len(s), bool)
    for k in range(5):
        tr = fold != k; te = fold == k
        best = max(np.unique(s[tr]), key=lambda th: (f1(s[tr] >= th, gold[tr]), -th))
        pred[te] = s[te] >= best
    return fold, pred


def methods(pairs, base):
    lab = lambda c: (base[c] != "disjoint").values
    sc = lambda c, t: (base[c].astype(float) >= t).values
    return {
        "Our approach": (pairs.System_Label != "disjoint").values,
        "Dandelion (0.75)": sc("Dandelion_Score", 0.75),
        "SBERT raw text (0.75)": sc("SBERT_raw_text", 0.75),
        "SBERT WHAT+HOW concat (0.75)": sc("SBERT_WHAT_HOW_concat", 0.75),
        "SBERT WHAT+HOW mean (0.75)": sc("SBERT_WHAT_HOW_mean", 0.75),
        "SBERT raw text, tuned on test (0.60)": sc("SBERT_raw_text", 0.60),
        "SBERT WHAT+HOW concat, tuned on test (0.60)": sc("SBERT_WHAT_HOW_concat", 0.60),
        "Dandelion, tuned on test (0.60)": sc("Dandelion_Score", 0.60),
        "TF-IDF raw text, tuned on test (0.20)": sc("TFIDF_cosine", 0.20),
        "TF-IDF raw text, 5-fold CV threshold": tfidf_cv(base, (pairs.Human_Majority != "disjoint").values)[1],
        "GPT-4o raw text R1": lab("GPT4o_raw_R1"), "GPT-4o raw text R2": lab("GPT4o_raw_R2"),
        "GPT-4o WHAT+HOW R1": lab("GPT4o_WHATHOW_R1"), "GPT-4o WHAT+HOW R2": lab("GPT4o_WHATHOW_R2"),
        "Claude Sonnet 5.5 raw text": lab("Claude_Sonnet55"), "Gemini 2.5 Flash raw text": lab("Gemini25Flash"),
        "GPT-4o WHAT+HOW with definitions R1": lab("GPT4o_WHATHOW_def_R1"),
        "GPT-4o WHAT+HOW with definitions R2": lab("GPT4o_WHATHOW_def_R2"),
    }


def tfidf_scores(wb):
    from sklearn.feature_extraction.text import TfidfVectorizer
    ideas = pd.read_excel(wb, S_IDEAS); pairs = pd.read_excel(wb, S_PAIRS)
    vec = TfidfVectorizer(lowercase=True, stop_words="english", sublinear_tf=True).fit(ideas.Idea_Text.tolist())
    a = vec.transform(pairs.Idea1_Text); b = vec.transform(pairs.Idea2_Text)
    return np.asarray(a.multiply(b).sum(1)).ravel()


def significance(pairs, base):
    gold = (pairs.Human_Majority != "disjoint").values
    M = methods(pairs, base); sysp = M["Our approach"]
    rng = np.random.RandomState(BOOT_SEED)
    idx = [rng.randint(0, len(gold), len(gold)) for _ in range(BOOT_B)]
    rows = []
    for name, p in M.items():
        if name == "Our approach":
            continue
        d, lo, hi = boot_f1_diff(sysp, p, gold, idx)
        b, c, pex = mcnemar_related(sysp, p, gold)
        bb, cc, x2, pacc = mcnemar_accuracy(sysp, p, gold)
        rows.append(dict(Comparison=f"Our approach vs {name}", F1_ours=f1(sysp, gold), F1_baseline=f1(p, gold),
                         Delta_F1=d, CI95_low=lo, CI95_high=hi, Significant_F1=bool(lo > 0 or hi < 0),
                         Related_found_only_by_ours=b, Related_found_only_by_baseline=c, Exact_McNemar_p_related=pex,
                         Accuracy_ours=float((sysp == gold).mean()), Accuracy_baseline=float((p == gold).mean()),
                         McNemar_accuracy_chi2=x2, McNemar_accuracy_p=pacc))
    return pd.DataFrame(rows)


def calibration(wb):
    t = pd.read_excel(wb, S_CAL)
    out = []
    for m in THR:
        for split in ("all", "train", "test"):
            d = t[t.Matcher == m] if split == "all" else t[(t.Matcher == m) & (t.Split == split)]
            for th in (0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90):
                p = d.Raw_Score >= th; g = d.Gold_Label == "positive"
                out.append(dict(Matcher=m, Split=split, Threshold=th, F1=f1(p.values, g.values)))
    w = t.pivot(index="Term_Pair_Group", columns="Matcher", values="Raw_Score")
    gold = t.groupby("Term_Pair_Group").Gold_Label.first().eq("positive").values
    links = {m: (w[m] >= THR[m]).values for m in THR}
    abl = []
    for combo in (["Linguistic"], ["Content"], ["Terminology"], ["Linguistic", "Content"], ["Linguistic", "Terminology"],
                  ["Content", "Terminology"], ["Linguistic", "Content", "Terminology"]):
        p = np.any([links[m] for m in combo], axis=0)
        r = binary(p, gold); abl.append(dict(Matchers="+".join(combo), **r))
    return pd.DataFrame(out), pd.DataFrame(abl), links


def screening(wb):
    """Candidate screening (sheet 20): keep a pair if the two idea texts share a content word."""
    d = pd.read_excel(wb, "20_Screening_R1-8", header=3, usecols="A:H")
    kept = d.N_Shared > 0
    s = d[d.In_240_Sample == 1]; rel = s.Human_Majority != "disjoint"
    return dict(all_pairs=len(d), kept=int(kept.sum()), avoided=1 - kept.mean(),
                related=int(rel.sum()), related_kept=int((rel & (s.N_Shared > 0)).sum()))


def llm_errors(wb, pairs, base):
    """Sheet 22: false positives on the pairs the annotators label disjoint, by label, shared content words, SBERT."""
    d = pd.read_excel(wb, "20_Screening_R1-8", header=3, usecols="A:H")
    nsh = d.dropna(subset=["Pair_ID"]).set_index("Pair_ID").N_Shared
    shared = pairs.Pair_ID.map(nsh).fillna(0).values > 0
    dis = (pairs.Human_Majority == "disjoint").values; sb = base.SBERT_raw_text.astype(float).values
    runs = [("Our approach", pairs.System_Label)] + [(c, base[c]) for c in
            ("GPT4o_raw_R1", "GPT4o_raw_R2", "GPT4o_WHATHOW_R1", "GPT4o_WHATHOW_R2",
             "GPT4o_WHATHOW_def_R1", "GPT4o_WHATHOW_def_R2", "Claude_Sonnet55", "Gemini25Flash")]
    rows = []
    for name, lab in runs:
        lab = lab.values; fp = dis & (lab != "disjoint"); tn = dis & (lab == "disjoint")
        rows.append(dict(Method=name, FP=int(fp.sum()), FP_alt=int((dis & (lab == "alternative-solution")).sum()),
                         FP_similar=int((dis & (lab == "similar")).sum()), TN=int(tn.sum()),
                         FP_shared=shared[fp].mean() if fp.any() else 0, TN_shared=shared[tn].mean() if tn.any() else 0,
                         SBERT_FP=sb[fp].mean() if fp.any() else 0, SBERT_TN=sb[tn].mean() if tn.any() else 0,
                         Shared_disjoint_labelled_related=(dis & shared & (lab != "disjoint")).sum() / (dis & shared).sum()))
    return pd.DataFrame(rows)


def stratified(pairs):
    """Sheet 23: F1 per Dandelion rank band and population-weighted estimate (R3-1)."""
    pop = pd.read_excel(S_WB, S_POP, usecols="A:J")
    popn = pop.Rank_Band.value_counts().to_dict()
    band = pairs.Rank_Band.str[0].values; g = (pairs.Human_Majority != "disjoint").values; s = (pairs.System_Label != "disjoint").values
    full = {k[0]: v for k, v in popn.items()}
    groups = {b: np.where(band == b)[0] for b in "ABCD" if (band == b).any()}

    def wf(idx):
        tp = fp = fn = 0.0
        for b in groups:
            m = idx[band[idx] == b]
            if len(m) == 0:
                continue
            w = full[b] / len(m)
            tp += w * (g[m] & s[m]).sum(); fp += w * (~g[m] & s[m]).sum(); fn += w * (g[m] & ~s[m]).sum()
        p = tp / (tp + fp); r = tp / (tp + fn)
        return p, r, 2 * p * r / (p + r)

    rows = []
    for b in "ABCD":
        m = band == b
        tp = int((g & s & m).sum()); fp = int((~g & s & m).sum()); fn = int((g & ~s & m).sum()); tn = int((~g & ~s & m).sum())
        rows.append(dict(Band=b, Population=full.get(b, 0), Annotated=int(m.sum()), TP=tp, FP=fp, FN=fn, TN=tn))
    p, r, f = wf(np.arange(len(g)))
    rng = np.random.RandomState(BOOT_SEED)
    bs = [wf(np.concatenate([rng.choice(groups[b], len(groups[b])) for b in groups]))[2] for _ in range(BOOT_B)]
    sp = pd.read_excel(S_WB, "23_Stratified_F_R3-1", header=18, usecols="N:Q").dropna(subset=["Pair_ID"])
    rk = {}
    for q in pop.itertuples():
        rk[(q.Idea1_ID, q.Idea2_ID)] = q.Dandelion_Rank_Idea1; rk[(q.Idea2_ID, q.Idea1_ID)] = q.Dandelion_Rank_Idea2
    assert all(rk[(q.Seed_Idea, q.Partner_Idea)] == q.Partner_Rank_in_Seed_List for q in sp.itertuples()), "partner ranks differ from sheet 03"
    rows_bands = {b: int(((sp.Partner_Rank_in_Seed_List >= lo) & (sp.Partner_Rank_in_Seed_List <= hi)).sum())
                  for b, lo, hi in (("1-5", 1, 5), ("6-10", 6, 10), ("11-30", 11, 30), ("31-79", 31, 79), ("80-94", 80, 94))}
    print("partner rank in the seed ranking:", rows_bands)
    return pd.DataFrame(rows), dict(P_weighted=p, R_weighted=r, F1_weighted=f,
                                    F1_CI95_low=float(np.percentile(bs, 2.5)), F1_CI95_high=float(np.percentile(bs, 97.5)))


def adelie(wb, pairs):
    """Sheet 24 (optional, R3-8): relatedness from ADELIE triples (word overlap), 5-fold CV threshold."""
    import json, re
    from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS as SW
    t = pd.read_excel(wb, "24_ADELIE_Optional_R3-8", header=3, usecols="A:E").dropna(subset=["Idea_ID"])
    T = {r.Idea_ID: (json.loads(r.ADELIE_Triples_JSON) if isinstance(r.ADELIE_Triples_JSON, str) and r.ADELIE_Triples_JSON else []) for r in t.itertuples()}
    tok = lambda x: {w for w in re.findall(r"[a-z]+", " ".join(str(x.get(k, "")) for k in ("subject", "predicate", "object")).lower()) if w not in SW and len(w) > 1}

    def score(a, b):
        if not T.get(a) or not T.get(b):
            return None
        return max((len(tok(x) & tok(y)) / len(tok(x) | tok(y)) for x in T[a] for y in T[b] if tok(x) | tok(y)), default=0.0)
    sc = [(score(r.Idea1_ID, r.Idea2_ID), r.Human_Majority != "disjoint", r.System_Label != "disjoint") for r in pairs.itertuples()]
    sc = [x for x in sc if x[0] is not None]
    s = np.array([x[0] for x in sc]); g = np.array([x[1] for x in sc]); ours = np.array([x[2] for x in sc])
    rng = np.random.RandomState(BOOT_SEED); fold = rng.permutation(len(s)) % 5; pred = np.zeros(len(s), bool)
    for k in range(5):
        tr = fold != k; te = fold == k
        best = max(np.unique(s[tr]), key=lambda th: (f1(s[tr] >= th, g[tr]), -th))
        pred[te] = s[te] >= best
    idx = [rng.randint(0, len(s), len(s)) for _ in range(BOOT_B)]
    d, lo, hi = boot_f1_diff(ours, pred, g, idx)
    return dict(scored_pairs=len(s), F1_adelie_cv=f1(pred, g), F1_ours_same_pairs=f1(ours, g), Delta_F1=d, CI95_low=lo, CI95_high=hi)


def cascade_orders(links):
    """All orders of the three threshold-dependent matchers: the first matcher that links a pair reports it."""
    rows = []
    for order in itertools.permutations(list(links)):
        reported = {m: 0 for m in links}; calls = 0
        for i in range(len(next(iter(links.values())))):
            for k, m in enumerate(order, 1):
                if links[m][i]:
                    reported[m] += 1; calls += k; break
            else:
                calls += len(order)
        linked = int(np.any(list(links.values()), axis=0).sum())
        rows.append(dict(Order=" > ".join(order), Linked=linked, **{f"Reported_{m}": v for m, v in reported.items()}, Calls=calls))
    return pd.DataFrame(rows)


def extraction(wb):
    e = pd.read_excel(wb, S_EXT)
    rows = []
    for pat in ("WHAT", "HOW"):
        d = e[e.Pattern == pat]; exp = int((d.Triple_Expected == "Y").sum())
        o_ext = int((d.OpenIE_Type == "triple").sum()); o_cor = int(((d.OpenIE_Type == "triple") & (d.OpenIE_Judgement == "Correct")).sum())
        status = np.where((d[["GPT4o_S", "GPT4o_P", "GPT4o_O"]] != "NONE").all(axis=1), "triple", "other")
        g_ext = int((status == "triple").sum())
        for name, ext, cor in (("Stanford OpenIE", o_ext, o_cor),
                               ("GPT-4o lenient", g_ext, int((d.Judgement_Lenient == "Correct").sum())),
                               ("GPT-4o strict", g_ext, int((d.Judgement_Strict == "Correct").sum()))):
            p = cor / ext if ext else 0; r = cor / exp if exp else 0
            rows.append(dict(Pattern=pat, Extractor=name, Extracted=ext, Correct=cor, Expected=exp,
                             Precision=p, Recall=r, F1=2 * p * r / (p + r) if p + r else 0))
    return pd.DataFrame(rows)


def wilson(k, n, z=1.959964):
    if n == 0:
        return float("nan"), float("nan")
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (c - h) / d, (c + h) / d


def paper_tables(wb, pairs, base, cal, out):
    """Tables 6, 7, 8, 9, 12, 13, 16-19 and 23 of the revised manuscript, from the raw data columns."""
    g = pairs.Human_Majority; s = pairs.System_Label
    gold = (g != "disjoint").values; sysb = (s != "disjoint").values
    order = ["disjoint", "alternative-solution", "similar", "duplicate", "generalises"]
    cm = pd.crosstab(pd.Categorical(g, order), pd.Categorical(s, order), rownames=["reference"], colnames=["system"],
                     margins=True, margins_name="Total", dropna=False)
    print("\n== Task 2, confusion matrix of our approach (Table 6) ==\n" + cm.to_string())
    out += [("table6_confusion", f"reference={a}", f"system={b}", int(cm.loc[a, b])) for a in order for b in order]
    print("\n== Task 2, per-class metrics with Wilson 95% CI (Table 7) ==")
    for c in order[:4]:
        tp = int(((g == c) & (s == c)).sum()); rn = int((g == c).sum()); pn = int((s == c).sum())
        P = tp / pn if pn else 0.0; R = tp / rn if rn else 0.0; F = 2 * P * R / (P + R) if P + R else 0.0
        (pl, ph), (rl, rh) = wilson(tp, pn), wilson(tp, rn)
        print(f"{c:22s} ref n={rn:3d} pred n={pn:3d}  P={P:.2f} [{pl:.2f}, {ph:.2f}]  R={R:.2f} [{rl:.2f}, {rh:.2f}]  F1={F:.2f}")
        out += [("table7_perclass", c, k, v) for k, v in (("P", P), ("P_low", pl), ("P_high", ph), ("R", R), ("R_low", rl), ("R_high", rh), ("F1", F))]
    det = (pairs.Default_Used == 0).values
    print("\n== Rule coverage (Table 8): pairs decided by a rule vs the default output disjoint ==")
    for name, m in (("Alternative-solution rule", det & (s == "alternative-solution").values), ("Similar rule", det & (s == "similar").values),
                    ("Duplicate rule", det & (s == "duplicate").values), ("Explicit Disjoint rule", det & (s == "disjoint").values),
                    ("All determined pairs", det), ("Undetermined pairs (default, Disjoint)", ~det)):
        n = int(m.sum()); k = int((m & (g == s).values).sum())
        print(f"{name:40s} pairs={n:3d} correct={k:3d} accuracy={k / n:.3f}")
        out += [("table8_rule_coverage", name, "pairs", n), ("table8_rule_coverage", name, "correct", k)]
    r = binary(sysb[det], gold[det])
    print(f"F1 on the determined pairs only (default rule disabled): {r['F1']:.3f}; false negatives from the default branch: "
          f"{int((~det & gold & ~sysb).sum())} of {int((gold & ~sysb).sum())}; false positives by label: "
          f"{pd.Series(s[~gold & sysb]).value_counts().to_dict()}")
    out += [("table8_rule_coverage", "determined pairs only", "F1", r["F1"])]
    print("\n== Relations detected per category (Table 9) ==")
    rows = [("Human reference", g), ("Our approach", s)]
    sim = lambda col, t: pd.Series(np.where(base[col].astype(float) >= t, "similar", "disjoint"))
    rows += [("Dandelion API (0.75)", sim("Dandelion_Score", 0.75)), ("SBERT raw text (0.75)", sim("SBERT_raw_text", 0.75)),
             ("TF-IDF (5-fold CV threshold)", pd.Series(np.where(base.TFIDF_CV_Related == 1, "similar", "disjoint")))]
    rows += [(c, base[c]) for c in ("GPT4o_raw_R1", "GPT4o_raw_R2", "GPT4o_WHATHOW_R1", "GPT4o_WHATHOW_R2", "Claude_Sonnet55",
                                    "Gemini25Flash", "GPT4o_WHATHOW_def_R1", "GPT4o_WHATHOW_def_R2")]
    t9 = pd.DataFrame({name: pd.Series(lab).value_counts().reindex(["similar", "alternative-solution", "disjoint", "duplicate", "generalises"]).fillna(0).astype(int)
                       for name, lab in rows}).T
    t9["Total"] = t9.sum(axis=1); print(t9.to_string())
    out += [("table9_counts", m, c, int(t9.loc[m, c])) for m in t9.index for c in t9.columns]
    print("\n== Threshold sweep of the similarity baselines, F1 (Table 12; thresholds chosen on test labels = upper bounds) ==")
    th = np.round(np.arange(0.05, 0.951, 0.05), 2)
    sw = pd.DataFrame({name: [binary(base[col].astype(float).values >= t, gold)["F1"] for t in th]
                       for name, col in (("SBERT raw text", "SBERT_raw_text"), ("SBERT WHAT+HOW", "SBERT_WHAT_HOW_concat"),
                                         ("Dandelion", "Dandelion_Score"), ("TF-IDF", "TFIDF_cosine"))}, index=th)
    print(sw.round(3).to_string())
    for c in sw.columns:
        print(f"best {c}: F1={sw[c].max():.3f} at {sw[c].idxmax():.2f}")
        out += [("table12_sweep", c, f"F1@{t:.2f}", v) for t, v in sw[c].items()]
    dl = np.where(base.Dandelion_Score.astype(float) >= 0.75, "Dandelion similar", "Dandelion disjoint")
    ours = s.replace({"duplicate": "similar or duplicate", "similar": "similar or duplicate"})
    ct = pd.crosstab(pd.Series(dl, name="Dandelion"), pd.Series(ours.values, name="our approach"), margins=True, margins_name="Total")
    print("\n== Our approach vs Dandelion (Table 13) ==\n" + ct.to_string())
    out += [("table13_cross", a, b, int(ct.loc[a, b])) for a in ct.index for b in ct.columns]
    t = pd.read_excel(wb, S_CAL)
    print("\n== Standalone matchers per term type at the selected thresholds (Tables 16-18; structure-based rows are kept from the original evaluation) ==")
    for tt, name in (("NounMatching", "Table 16 nouns"), ("VerbMatching", "Table 17 predicates"), ("SentenceMatching", "Table 18 sequences of words")):
        for m in THR:
            d = t[(t.Term_Type_Source == tt) & (t.Matcher == m)]
            r = binary((d.Raw_Score >= THR[m]).values, (d.Gold_Label == "positive").values)
            print(f"{name:28s} n={len(d):3d} {m:12s} P={r['Precision']:.2f} R={r['Recall']:.2f} F1={r['F1']:.2f}")
            out += [("tables16_18_matchers", f"{name} {m}", k, r[k]) for k in ("Precision", "Recall", "F1")]
    print("\n== F1 per matcher at the selected threshold on the term pairs (Table 19) ==")
    for m in THR:
        v = {sp: float(cal[(cal.Matcher == m) & (cal.Split == sp) & (np.isclose(cal.Threshold, THR[m]))].F1.iloc[0]) for sp in ("all", "train", "test")}
        flat = cal[(cal.Matcher == m) & (cal.Split == "all") & (cal.Threshold >= 0.6)].F1.nunique() == 1
        print(f"{m:12s} threshold {THR[m]:.2f}: all {v['all']:.3f}, calibration {v['train']:.3f}, held-out {v['test']:.3f}"
              f"{'  (same F1 at every threshold 0.60-0.90)' if flat else ''}")
        out += [("table19_calibration", m, sp, x) for sp, x in v.items()]
    print("\n== Upper bound with perfect extraction (Table 23) ==")
    tp, fp, fn = int((gold & sysb).sum()), int((~gold & sysb).sum()), int((gold & ~sysb).sum())
    for k in (0, 3, 5, fn):
        P = (tp + k) / (tp + k + fp); R = (tp + k) / (tp + fn); F = 2 * P * R / (P + R)
        print(f"missed pairs recovered {k} of {fn}: TP={tp + k} FP={fp} FN={fn - k} P={P:.2f} R={R:.2f} F1={F:.3f}")
        out += [("table23_upper_bound", f"{k} of {fn} recovered", "F1", F)]


def main(wb):
    global S_WB
    S_WB = wb
    pairs, base = load(wb)
    gold = (pairs.Human_Majority != "disjoint").values
    out = []
    print("== Task 1, binary metrics (Tables 5 and 10) ==")
    for name, p in methods(pairs, base).items():
        r = binary(p, gold); out += [("binary", name, k, v) for k, v in r.items()]
        print(f"{name:40s} TP={r['TP']:3d} FP={r['FP']:3d} FN={r['FN']:3d} TN={r['TN']:3d} "
              f"P={r['Precision']:.3f} R={r['Recall']:.3f} F1={r['F1']:.3f} Acc={r['Accuracy']:.3f}")
    if "TFIDF_CV_Related" in base:
        same = (tfidf_cv(base, gold)[1] == (base.TFIDF_CV_Related.values == 1)).all()
        print("TF-IDF cross-validated predictions identical to sheet 04, column T:", bool(same))
    print("\n== Task 2, five-way macro metrics, four scored classes (Table 11) ==")
    gl = pairs.Human_Majority.tolist()
    for name, col in (("Our approach", None), ("GPT-4o raw text R1", "GPT4o_raw_R1"), ("GPT-4o raw text R2", "GPT4o_raw_R2"),
                      ("GPT-4o WHAT+HOW R1", "GPT4o_WHATHOW_R1"), ("GPT-4o WHAT+HOW R2", "GPT4o_WHATHOW_R2"),
                      ("Claude Sonnet 5.5", "Claude_Sonnet55"), ("Gemini 2.5 Flash", "Gemini25Flash"),
                      ("GPT-4o WHAT+HOW def. R1", "GPT4o_WHATHOW_def_R1"), ("GPT-4o WHAT+HOW def. R2", "GPT4o_WHATHOW_def_R2")):
        pl = pairs.System_Label.tolist() if col is None else base[col].tolist()
        rows, m = macro(pl, gl); out += [("macro", name, k, v) for k, v in m.items()]
        print(f"{name:22s} macro P={m['macro_P']:.3f} R={m['macro_R']:.3f} F1={m['macro_F1']:.3f}")
    for a, b in (("GPT4o_raw_R1", "GPT4o_raw_R2"), ("GPT4o_WHATHOW_R1", "GPT4o_WHATHOW_R2"),
                 ("GPT4o_WHATHOW_def_R1", "GPT4o_WHATHOW_def_R2")):
        k, ch = cohen_kappa(base[a], base[b]); out += [("kappa", f"{a} vs {b}", "kappa", k), ("kappa", f"{a} vs {b}", "share_changed", ch)]
        print(f"kappa {a} vs {b}: {k:.3f} (pairs changed {100 * ch:.1f}%)")
    fk, ka, unan = fleiss_kripp(pairs[["Annotator_A", "Annotator_B", "Annotator_C"]].values)
    out += [("agreement", "annotators", "fleiss_kappa", fk), ("agreement", "annotators", "krippendorff_alpha", ka)]
    print(f"\nAnnotator agreement: Fleiss kappa={fk:.4f}  Krippendorff alpha={ka:.4f}  all three agree={unan:.3f}")
    print("\n== Significance, Section 7.4 (paired bootstrap, seed %d, %d resamples) ==" % (BOOT_SEED, BOOT_B))
    sig = significance(pairs, base)
    for r in sig.itertuples():
        print(f"{r.Comparison:62s} dF1={r.Delta_F1:+.3f} [{r.CI95_low:+.3f},{r.CI95_high:+.3f}] "
              f"related only ours/baseline={r.Related_found_only_by_ours}/{r.Related_found_only_by_baseline} p={r.Exact_McNemar_p_related:.4f} "
              f"acc McNemar p={r.McNemar_accuracy_p:.4f}")
        out += [("significance", r.Comparison, k, getattr(r, k)) for k in ("Delta_F1", "CI95_low", "CI95_high", "Exact_McNemar_p_related", "McNemar_accuracy_p")]
    st_rows, st = stratified(pairs)
    print("\n== F1 by Dandelion rank band and population-weighted estimate (Section 6.5, sheet 23) ==\n" + st_rows.to_string(index=False))
    print("weighted P=%.3f R=%.3f F1=%.3f, 95%% CI [%.3f, %.3f]" % (st["P_weighted"], st["R_weighted"], st["F1_weighted"], st["F1_CI95_low"], st["F1_CI95_high"]))
    out += [("stratified", "weighted estimate", k, v) for k, v in st.items()]
    try:
        ad = adelie(wb, pairs)
        print("\n== Optional: ADELIE triples (response letter, sheet 24) ==\n" + ", ".join(f"{k}={v:.3f}" if isinstance(v, float) else f"{k}={v}" for k, v in ad.items()))
        out += [("adelie_optional", "ADELIE vs ours", k, v) for k, v in ad.items()]
    except ImportError:
        print("\nscikit-learn not installed: ADELIE check skipped")
    le = llm_errors(wb, pairs, base)
    print("\n== LLM error analysis (Section 7.5, sheet 22) ==\n" + le.round(3).to_string(index=False))
    out += [("llm_errors", r.Method, k, getattr(r, k)) for r in le.itertuples() for k in le.columns if k != "Method"]
    cal, abl, links = calibration(wb)
    print("\n== Matcher ablation on term pairs (Table 20) ==\n" + abl[["Matchers", "Precision", "Recall", "F1"]].round(3).to_string(index=False))
    orders = cascade_orders(links)
    print("\n== Cascade order, all 6 orders (Table 21) ==\n" + orders.to_string(index=False))
    out += [("cascade_order", r.Order, k, getattr(r, k)) for r in orders.itertuples() for k in orders.columns if k != "Order"]
    sc = screening(wb)
    print(f"\n== Candidate screening by shared content word (Section 9.6) ==\nall pairs {sc['all_pairs']}, kept {sc['kept']} "
          f"(avoided {100 * sc['avoided']:.1f}%), related pairs kept {sc['related_kept']}/{sc['related']}")
    out += [("screening", "shared content word", k, v) for k, v in sc.items()]
    paper_tables(wb, pairs, base, cal, out)
    ext = extraction(wb)
    print("\n== Triple extraction: triple rows of Table 15 and the LLM extractor (Section 9.5) ==\n" + ext.round(3).to_string(index=False))
    try:
        t = tfidf_scores(wb); dif = np.abs(t - base.TFIDF_cosine.values).max()
        print(f"\nTF-IDF recomputed, max difference to workbook: {dif:.2e}")
    except ImportError:
        print("\nscikit-learn not installed: TF-IDF check skipped")
    pd.DataFrame(out, columns=["Block", "Method", "Metric", "Value"]).to_csv("evaluate_output.csv", index=False)
    print("\nWritten: evaluate_output.csv")
    return sig, cal, abl, ext


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/idea_relationships_data.xlsx")
