"""Export the reported outputs of every experiment from the data workbook into the experiment folders.

    python experiments/export_outputs.py

The files in */outputs/ without '_rerun' in their name are written by this script: they hold exactly the values
of the workbook, i.e. the values behind the manuscript tables. The run scripts write *_rerun files next to them.
"""
import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from common import S_ADELIE, S_BASE, S_EXT, S_SCREEN, sheet  # noqa: E402

LLM_RUNS = {
    "GPT4o_raw_R1": "GPT-4o, raw text, run 1 (ChatGPT app, Oct 2026)",
    "GPT4o_raw_R2": "GPT-4o, raw text, run 2 (ChatGPT app, Oct 2026)",
    "GPT4o_WHATHOW_R1": "GPT-4o, WHAT+HOW, run 1 (ChatGPT app, fresh chat, Oct 2026)",
    "GPT4o_WHATHOW_R2": "GPT-4o, WHAT+HOW, run 2 (ChatGPT app, fresh chat, Oct 2026)",
    "GPT4o_WHATHOW_def_R1": "GPT-4o, WHAT+HOW with definitions, run 1 (ChatGPT app, 8 Nov 2026)",
    "GPT4o_WHATHOW_def_R2": "GPT-4o, WHAT+HOW with definitions, run 2 (ChatGPT app, 8 Nov 2026)",
    "Claude_Sonnet55": "Claude Sonnet 5.5, raw text, single run (Oct 2026)",
    "Gemini25Flash": "Gemini 2.5 Flash, raw text, single run (Oct 2026)",
}


def write(df, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8")
    print(f"written {path.relative_to(HERE.parent)} ({len(df)} rows)")


def main():
    b = sheet(S_BASE)
    write(b[["Pair_ID", "SBERT_raw_text", "SBERT_WHAT_HOW_concat", "SBERT_WHAT_HOW_mean"]], HERE / "01_sbert" / "outputs" / "sbert_scores.csv")
    write(b[["Pair_ID", "TFIDF_cosine", "TFIDF_CV_Fold", "TFIDF_CV_Related"]], HERE / "02_tfidf" / "outputs" / "tfidf_scores.csv")
    write(b[["Pair_ID", "Dandelion_Score"]], HERE / "02_tfidf" / "outputs" / "dandelion_scores_original_study.csv")
    llm = HERE / "03_llm_pair_classification" / "outputs"
    for c in LLM_RUNS:
        d = b[["Pair_ID", c]].rename(columns={c: "label"})
        if c.startswith("GPT4o_WHATHOW_R"):
            d["input_differs_from_sheet01"] = b.iloc[:, 15].astype(int)
        write(d, llm / f"{c}.csv")
    pd.DataFrame([dict(file=f"{c}.csv", workbook_column=f"sheet 04, {c}", run=v) for c, v in LLM_RUNS.items()]).to_csv(
        llm / "runs.csv", index=False)

    e = sheet(S_EXT, usecols="A:Q").dropna(subset=["Item"])
    e["GPT4o_Status"] = ["triple" if all(x != "NONE" for x in r) else ("none" if all(x == "NONE" for x in r) else "partial")
                         for r in e[["GPT4o_S", "GPT4o_P", "GPT4o_O"]].astype(str).values]
    write(e, HERE / "04_triple_extraction" / "outputs" / "openie_vs_gpt4o_judged.csv")

    a = sheet(S_ADELIE, header=3, usecols="A:E").dropna(subset=["Idea_ID"])
    a["ADELIE_Triples_JSON"] = a.ADELIE_Triples_JSON.fillna("")
    write(a, HERE / "05_adelie_optional" / "outputs" / "adelie_triples.csv")
    p = sheet(S_ADELIE, header=3, usecols="G:L").dropna(subset=["Pair_ID"])
    for c in ("Fold", "ADELIE_CV_Related"):
        p[c] = p[c].astype("Int64")
    write(p, HERE / "05_adelie_optional" / "outputs" / "adelie_pair_scores.csv")

    s = sheet(S_SCREEN, header=3, usecols="A:D").dropna(subset=["Idea1_ID"])
    s["Shared_Content_Words"] = s.Shared_Content_Words.fillna("")
    write(s, HERE / "07_candidate_screening" / "outputs" / "shared_content_words.csv")


if __name__ == "__main__":
    main()
