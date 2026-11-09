"""Candidate screening by shared content words (sheet 20; Section 9.6, Reviewer 1, comment 8).

    python experiments/07_candidate_screening/screening.py

All 1,326 pairs of the 52 test ideas. A pair is kept if the two idea texts share at least one content word:
lower-cased tokens, the stop words of the framework (framework/v1/src/idearel/text.py) removed, nouns lemmatised
with WordNet (NLTK). Prints the comparisons avoided and the related test pairs kept, writes
outputs/shared_content_words_rerun.csv and compares it with the workbook. Needs: pip install nltk, then
python -c "import nltk; nltk.download('wordnet')".
"""
import itertools
import re
import sys
from pathlib import Path

import pandas as pd
from nltk.stem import WordNetLemmatizer

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from common import S_IDEAS, check_equal, reference, sheet  # noqa: E402

# same list as framework/v1/src/idearel/text.py
DETERMINERS = {"a", "an", "the", "this", "that", "these", "those", "its", "their", "his", "her", "our", "my", "your"}
STOPWORDS = DETERMINERS | {"of", "to", "in", "on", "for", "with", "and", "or", "by", "at", "from", "into", "is", "are",
                           "be", "can", "will", "as", "if", "when", "there", "so"}


def content_words(text):
    return [t for t in re.findall(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)*", (text or "").lower()) if t not in STOPWORDS]


def main():
    lem = WordNetLemmatizer()
    ideas = sheet(S_IDEAS)
    W = {r.Idea_ID: {lem.lemmatize(w) for w in content_words(r.Idea_Text)} for r in ideas.itertuples()}
    rows = [dict(Idea1_ID=a, Idea2_ID=b, Shared_Content_Words=", ".join(sorted(W[a] & W[b])), N_Shared=len(W[a] & W[b]))
            for a, b in itertools.combinations(ideas.Idea_ID, 2)]
    out = pd.DataFrame(rows)
    (HERE / "outputs").mkdir(exist_ok=True)
    out.to_csv(HERE / "outputs" / "shared_content_words_rerun.csv", index=False)

    kept = out.N_Shared > 0
    ref = reference(); key = {frozenset((r.Idea1_ID, r.Idea2_ID)): r.Related for r in ref.itertuples()}
    out["Related"] = [key.get(frozenset((a, b))) for a, b in zip(out.Idea1_ID, out.Idea2_ID)]
    s = out.dropna(subset=["Related"]); rel = s.Related == 1
    print(f"all pairs {len(out)}, kept {int(kept.sum())}, comparisons avoided {100 * (1 - kept.mean()):.1f}%")
    print(f"test pairs {len(s)}: kept {int((s.N_Shared > 0).sum())}; related {int(rel.sum())}, related kept "
          f"{int((rel & (s.N_Shared > 0)).sum())} (recall {(rel & (s.N_Shared > 0)).sum() / rel.sum():.2f})")
    old = pd.read_csv(HERE / "outputs" / "shared_content_words.csv").fillna("")
    check_equal(out.Shared_Content_Words, old.Shared_Content_Words, "Shared_Content_Words")


if __name__ == "__main__":
    main()
