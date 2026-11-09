"""Sampling design of the 240 test pairs (sheets 03 and 23; Sections 6.1 and 6.5, Reviewer 3, comment 1).

    python experiments/06_sampling_strata/sampling_pattern.py

Reads the population of 4,465 pairs (95 ideas) with their Dandelion similarity ranks (sheet 03) and the seed idea
of each test pair (sheet 23, columns N-R) and prints:
  1. population and test pairs per rank band (minimum rank over the two ideas: A 1-5, B 6-30, C 31-79, D >= 80);
  2. where each partner sits in its seed idea's own ranking (1-5, 6-10, 11-30, 31-79, 80-94);
  3. how many seed ideas also received partners from the least similar end of their ranking.
The Dandelion ranks come from the original study (the Dandelion API was discontinued in 2023).
The F-measure per band, the population-weighted estimate and its stratified-bootstrap interval are computed by
evaluate.py (stratified()).
"""
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from common import S_PAIRS, S_POP, S_STRAT, sheet  # noqa: E402

BANDS = [("1-5", 1, 5), ("6-10", 6, 10), ("11-30", 11, 30), ("31-79", 31, 79), ("80-94", 80, 94)]


def main():
    pop = sheet(S_POP, usecols="A:K")
    pairs = sheet(S_PAIRS)
    sp = sheet(S_STRAT, header=18, usecols="N:R").dropna(subset=["Pair_ID"])

    t = pd.DataFrame(dict(Population=pop.Rank_Band.value_counts(), In_test_240=pop[pop.In_Test_240 == 1].Rank_Band.value_counts(),
                          Related_in_test=pairs[pairs.Human_Majority.str.strip() != "disjoint"].Rank_Band.value_counts())).fillna(0).astype(int)
    print("1. Pairs per Dandelion rank band (minimum rank of the two ideas)\n" + t.sort_index().to_string())
    print(f"   total: population {t.Population.sum()}, test {t.In_test_240.sum()}; "
          f"stratum Top5 = band A ({t.In_test_240.iloc[0]} pairs), NonTop5 = bands B-D ({t.In_test_240.iloc[1:].sum()} pairs)")

    rank = {}
    for q in pop.itertuples():
        rank[(q.Idea1_ID, q.Idea2_ID)] = q.Dandelion_Rank_Idea1; rank[(q.Idea2_ID, q.Idea1_ID)] = q.Dandelion_Rank_Idea2
    assert all(rank[(q.Seed_Idea, q.Partner_Idea)] == q.Partner_Rank_in_Seed_List for q in sp.itertuples()), \
        "partner ranks in sheet 23 differ from sheet 03"
    r = sp.Partner_Rank_in_Seed_List
    print("\n2. Rank of the partner in its seed idea's own ranking (checked against sheet 03)")
    for name, lo, hi in BANDS:
        print(f"   {name:>6}: {int(((r >= lo) & (r <= hi)).sum()):3d}")
    print(f"   among the 30 most similar: {int((r <= 30).sum())}")
    low = sp[r >= 80].Seed_Idea.nunique()
    print(f"\n3. Seed ideas: {sp.Seed_Idea.nunique()}; with partners from the least similar end (rank >= 80): {low}")


if __name__ == "__main__":
    main()
