"""Score LLM label files against the annotator reference (Tables 9, 10, 11 of the revised manuscript).

    python experiments/03_llm_pair_classification/score_llm.py                    # the eight reported runs
    python experiments/03_llm_pair_classification/score_llm.py my_run.csv         # any file with Pair_ID, label
    python experiments/03_llm_pair_classification/score_llm.py run1.csv run2.csv  # also Cohen's kappa between runs

A label file has the columns Pair_ID and label (a pasted chat table saved as CSV or TSV also works). Labels are
normalised ('alternative solution' -> alternative-solution, 'generalize' -> generalises, ...); anything else is
INVALID and counts as related in Task 1 and as wrong in Task 2.
Task 1: related = any label except disjoint. Task 2: macro P/R/F1 over disjoint, alternative-solution, similar,
duplicate (generalises has no human case and is not scored).
"""
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from common import S_BASE, binary, check_equal, cohen_kappa, macro, norm_label, reference, sheet  # noqa: E402

PAIRS_OF_RUNS = [("GPT4o_raw_R1", "GPT4o_raw_R2"), ("GPT4o_WHATHOW_R1", "GPT4o_WHATHOW_R2"),
                 ("GPT4o_WHATHOW_def_R1", "GPT4o_WHATHOW_def_R2")]


def read_labels(path):
    path = Path(path)
    sep = "\t" if path.suffix.lower() in (".tsv", ".txt") else ","
    d = pd.read_csv(path, sep=sep, dtype=str)
    if "Pair_ID" not in d.columns:                                  # pasted table without a header
        d = pd.read_csv(path, sep=sep, header=None, dtype=str).iloc[:, :2]
        d.columns = ["Pair_ID", "label"]
    d = d.rename(columns={d.columns[1]: "label"}) if "label" not in d.columns else d
    d["Pair_ID"] = d.Pair_ID.str.strip()
    return d.drop_duplicates("Pair_ID").set_index("Pair_ID").label.map(norm_label)


def score(name, labels, ref):
    lab = labels.reindex(ref.Pair_ID).fillna("INVALID").tolist()
    missing = int(labels.reindex(ref.Pair_ID).isna().sum()); invalid = sum(l == "INVALID" for l in lab)
    b = binary([l != "disjoint" for l in lab], ref.Related.astype(bool)); m = macro(lab, ref.Human_Majority.tolist())
    return dict(Run=name, Missing=missing, Invalid=invalid, **{k: b[k] for k in ("TP", "FP", "FN", "TN")},
                P=b["Precision"], R=b["Recall"], F1=b["F1"], macro_P=m["macro_P"], macro_R=m["macro_R"],
                macro_F1=m["macro_F1"]), lab


def main(files):
    ref = reference()
    if not files:
        files = [HERE / "outputs" / f"{c}.csv" for pair in PAIRS_OF_RUNS for c in pair] + \
                [HERE / "outputs" / "Claude_Sonnet55.csv", HERE / "outputs" / "Gemini25Flash.csv"]
    rows, labs = [], {}
    for f in files:
        r, lab = score(Path(f).stem, read_labels(f), ref); rows.append(r); labs[Path(f).stem] = lab
    print(pd.DataFrame(rows).round(3).to_string(index=False))
    pairs = PAIRS_OF_RUNS if not sys.argv[1:] else ([tuple(labs)] if len(labs) == 2 else [])
    for a, b in pairs:
        if a in labs and b in labs:
            k, ch = cohen_kappa(labs[a], labs[b])
            print(f"Cohen kappa {a} vs {b}: {k:.3f} (labels changed on {100 * ch:.1f}% of the pairs)")
    if not sys.argv[1:]:
        base = sheet(S_BASE)
        for name, lab in labs.items():
            check_equal(lab, base[name].map(norm_label), f"outputs/{name}.csv vs sheet 04")


if __name__ == "__main__":
    main(sys.argv[1:])
