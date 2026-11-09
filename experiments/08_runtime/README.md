# Runtime (sheet 21; Table 24 and Section 9.6)

**Part A, original prototype.** About 40 minutes for the 240 test pairs (about 10 s per pair) on an Intel Core i7,
16 GB RAM, Windows, with local DBpedia Spotlight, DBpedia and Wikidata, no cache and no screening. This is an
observation of the authors, not a controlled benchmark; the prototype is not part of this repository.

**Part B, released implementation (controlled benchmark).** Produced by the benchmark of the framework:

```bash
cd framework/v1
python scripts/benchmark.py --sizes 10 20 30 40 52 --out results/benchmark.csv
```

For each size n, the first n ideas of `data/ideas.csv` are compared exhaustively (n(n-1)/2 pairs), with and without
the link cache, in a fresh pipeline each time. The output reports start-up, extraction and comparison times, time
per pair, link requests, cache hits and the calls of each matcher, with the hardware and Python version.
`framework/v1/results/benchmark.csv` is the run reported in sheet 21 (Intel Xeon 2.3 GHz, 2 cores, 7.8 GB RAM,
Linux, Python 3.13). Times on another machine will differ; the matcher calls and cache hits do not depend on the
machine.

**Part C, extrapolation.** Formulas in sheet 21: time per pair from parts A and B times n(n-1)/2, with and without
the share of pairs kept by the candidate screening (`07_candidate_screening`).
