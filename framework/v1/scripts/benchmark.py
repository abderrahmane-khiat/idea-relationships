"""Efficiency at different dataset sizes (Reviewer 1, comment 8).

    python scripts/benchmark.py [--sizes 10 20 30 40 52] [--out results/benchmark.csv]

For each size n, the first n ideas of data/ideas.csv are compared exhaustively (n(n-1)/2 pairs),
once with the link cache of the cascade and once without it, in a fresh pipeline each time. Reported:
start-up time (loading WordNet, word vectors, spaCy), extraction time, comparison time, time per pair,
matcher calls (a structure-matcher call corresponds to one knowledge-graph query with the SPARQL
backend), and the cache hit rate. The hardware and software are printed and written to the output.
"""
import argparse
import csv
import itertools
import os
import platform
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from idearel import Framework, load_config  # noqa: E402
from idearel.evaluation import load_ideas  # noqa: E402


def hardware():
    cpu = platform.processor() or ""
    try:
        for line in open("/proc/cpuinfo"):
            if line.startswith("model name"):
                cpu = line.split(":", 1)[1].strip(); break
    except OSError:
        pass
    try:
        ram = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 2 ** 30
    except (ValueError, AttributeError, OSError):
        ram = float("nan")
    return {"cpu": cpu, "cores": os.cpu_count(), "ram_gb": round(ram, 1), "os": f"{platform.system()} {platform.release()}",
            "python": platform.python_version()}


def run(ideas, n, cache):
    t0 = time.perf_counter()
    fw = Framework(load_config(overrides={"cascade.cache": str(cache).lower()}))
    sel = sorted(ideas)[:n]
    fw.compare(ideas[sel[0]], ideas[sel[1]])          # forces lazy loading of all resources
    fw.cascade.stats.clear(); fw._elements.clear(); fw.cascade._cache.clear()
    t1 = time.perf_counter()
    for i in sel:
        fw.elements(ideas[i])
    t2 = time.perf_counter()
    pairs = list(itertools.combinations(sel, 2))
    for a, b in pairs:
        fw.compare(ideas[a], ideas[b])
    t3 = time.perf_counter()
    st = fw.cascade.stats
    return {"ideas": n, "pairs": len(pairs), "cache": cache, "startup_s": round(t1 - t0, 2),
            "extraction_s": round(t2 - t1, 3), "comparison_s": round(t3 - t2, 3),
            "ms_per_pair": round(1000 * (t3 - t2) / len(pairs), 2),
            "link_requests": st["requests"], "cache_hits": st["cache_hits"],
            "cache_hit_rate": round(st["cache_hits"] / st["requests"], 3) if st["requests"] else 0,
            **{k: st[k] for k in ("calls_structure", "calls_linguistic", "calls_content", "calls_terminology")}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sizes", type=int, nargs="+", default=[10, 20, 30, 40, 52])
    ap.add_argument("--out", default=str(ROOT / "results" / "benchmark.csv"))
    a = ap.parse_args()
    ideas = load_ideas()
    hw = hardware()
    print("Hardware:", hw)
    rows = []
    for n in a.sizes:
        for cache in (True, False):
            r = run(ideas, min(n, len(ideas)), cache)
            rows.append({**r, **hw})
            print({k: r[k] for k in ("ideas", "pairs", "cache", "comparison_s", "ms_per_pair", "cache_hit_rate", "calls_structure")})
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
