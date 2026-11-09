"""Terminal version of the framework.

    idearel compare  --what1 "..." --how1 "..." --what2 "..." --how2 "..."
    idearel compare  --idea1 "free text" --idea2 "free text"
    idearel extract  --what "..." --how "..."
    idearel batch    --ideas data/ideas.csv [--pairs data/pairs.csv] --out results/batch.csv
    idearel evaluate [--out-dir results]
    idearel ablation | orders | calibrate [--apply]
    idearel rules    [--case T-T] [--pattern WHAT|HOW]
    idearel check
    idearel serve    [--port 8000]

Common options: --config FILE, --set key=value (repeatable), --extractor NAME.
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
import textwrap
from pathlib import Path

from .config import ROOT, load_config, parse_set_args


# ------------------------------------------------------------------ helpers
def build_config(args) -> dict:
    over = parse_set_args(getattr(args, "set", None))
    if getattr(args, "extractor", None):
        over["extractor"] = args.extractor
    if getattr(args, "segmenter", None):
        over["segmenter"] = args.segmenter
    return load_config(getattr(args, "config", None), over)


def framework(args):
    from .pipeline import Framework
    return Framework(build_config(args))


def fmt_element(e: dict) -> str:
    if e["type"] == "triple":
        return f"triple <{e['subject']} | {e['predicate']} | {e['object']}>"
    if e["type"] == "empty":
        return "empty"
    return f"{e['type'].replace('_', ' ')} \"{e['text']}\""


def print_decision(d, verbose=True):
    bar = "=" * 78
    print(bar)
    print(f"RELATIONSHIP: {d.relationship.value.upper()}" + (f"   ({d.direction})" if d.direction else ""))
    print(f"Decided by:   {d.rule_text}")
    if d.how_rule_id == "-":
        pass
    else:
        print(f"HOW:          {'same' if d.how_same else 'different'}  (rule {d.how_rule_id})")
    print(bar)
    if not verbose:
        return
    print("Step 2 - elements")
    for k in ("idea1", "idea2"):
        for p in ("WHAT", "HOW"):
            print(f"  {k} {p:<4}: {fmt_element(d.elements[k][p])}  [{d.elements[k][p].get('source', '')}]")
    print("Step 3 - links (cascade)")
    for l in d.links:
        print(f"  '{l['term1']}' ~ '{l['term2']}' -> {l['link']}" + (f"  by {l['matcher']}" if l['matcher'] else ""))
        for c in l["calls"]:
            score = "" if c["score"] is None else f"score {c['score']}"
            thr = "" if c["threshold"] is None else f" / thr {c['threshold']}"
            print(f"      {c['matcher']:<12} {c['link']:<11} {score}{thr}  {c['detail']}")
    print("Step 4 - codes:", ", ".join(f"{k}={v}" for k, v in d.codes.items()))
    for n in d.notes:
        print("  note:", n)


# ------------------------------------------------------------------ commands
def cmd_compare(args):
    from .models import Idea
    fw = framework(args)
    i1 = Idea("IDEA1", args.idea1 or "", args.what1 or "", args.how1 or "", "")
    i2 = Idea("IDEA2", args.idea2 or "", args.what2 or "", args.how2 or "", "")
    if not (i1.what or i1.text) or not (i2.what or i2.text):
        sys.exit("give --what1/--how1 and --what2/--how2, or --idea1/--idea2")
    d = fw.compare(i1, i2)
    if args.json:
        print(json.dumps(d.to_dict(), indent=2))
    else:
        print_decision(d, verbose=not args.quiet)


def cmd_extract(args):
    fw = framework(args)
    w = fw.extractor.extract(args.what or "", "WHAT", {"idea_id": ""})
    from .rules.engine import what_head
    h = fw.extractor.extract(args.how or "", "HOW", {"idea_id": "", "what_head": what_head(w)})
    print("WHAT:", fmt_element(w.to_dict()), f"[{w.source}]")
    print("HOW :", fmt_element(h.to_dict()), f"[{h.source}]")


def cmd_batch(args):
    from .evaluation import load_ideas, load_pairs, run_pairs, write_rows
    fw = framework(args)
    ideas = load_ideas(args.ideas)
    if args.pairs:
        pairs = load_pairs(args.pairs)
    else:
        pairs = [{"Pair_ID": f"P{n:06d}", "Idea1_ID": a, "Idea2_ID": b}
                 for n, (a, b) in enumerate(itertools.combinations(sorted(ideas), 2), 1)]
    res = run_pairs(fw, pairs, ideas, progress=_progress)
    write_rows(args.out, res)
    print(f"\nwrote {args.out} ({len(res)} pairs)")


def _progress(i, n):
    if i == n or i % 10 == 0:
        print(f"\r  {i}/{n} pairs", end="", file=sys.stderr, flush=True)


def _table(rows, cols):
    widths = [max(len(str(c)), *(len(f"{r.get(c, '')}") for r in rows)) for c in cols]
    print("  ".join(str(c).ljust(w) for c, w in zip(cols, widths)))
    for r in rows:
        print("  ".join(f"{r.get(c, '')}".ljust(w) for c, w in zip(cols, widths)))


def cmd_evaluate(args):
    from .evaluation import load_ideas, load_pairs, run_pairs, summarise, write_rows
    fw = framework(args)
    res = run_pairs(fw, load_pairs(args.pairs), load_ideas(args.ideas), progress=_progress)
    s = summarise(res)
    out = Path(args.out_dir); out.mkdir(parents=True, exist_ok=True)
    write_rows(out / "evaluation_pairs.csv", res)
    (out / "evaluation_summary.json").write_text(json.dumps(s, indent=2), encoding="utf-8")
    b, o = s["binary"], s["original_system_binary"]
    print(f"\n\nTask 1 (binary related vs disjoint), reference = Human_Majority, n = {s['n_pairs']}")
    rows = [{"system": "this implementation", **{k: (round(v, 3) if isinstance(v, float) else v) for k, v in b.items()}}]
    if o:
        rows.append({"system": "original system (paper)", **{k: (round(v, 3) if isinstance(v, float) else v) for k, v in o.items()}})
    _table(rows, ["system", "TP", "FP", "FN", "TN", "precision", "recall", "f1", "accuracy"])
    lo, hi = s["binary_f1_95ci"]
    print(f"  95% bootstrap CI of F1 (this implementation): [{lo:.3f}, {hi:.3f}]")
    m = s["five_way"]["macro"]
    print(f"\nTask 2 (five-way) macro P/R/F1 over {', '.join(s['five_way']['per_class'])}: "
          f"{m['precision']:.3f} / {m['recall']:.3f} / {m['f1']:.3f}")
    if s["agreement_with_original_system"]:
        a = s["agreement_with_original_system"]
        print(f"Agreement with the original System_Label: {a['accuracy']:.3f} (Cohen kappa {a['cohen_kappa']:.3f})")
    print("Rules used:", ", ".join(f"{k}:{v}" for k, v in s["rule_usage"].items()))
    print(f"\nwrote {out / 'evaluation_pairs.csv'} and {out / 'evaluation_summary.json'}")


def cmd_ablation(args):
    from .evaluation import ablation, load_ideas, load_pairs, write_rows
    rows = ablation(build_config(args), load_pairs(args.pairs), load_ideas(args.ideas))
    _table(rows, ["matchers", "TP", "FP", "FN", "precision", "recall", "f1"])
    write_rows(Path(args.out_dir) / "ablation.csv", rows)


def cmd_orders(args):
    from .evaluation import cascade_orders, load_ideas, load_pairs, write_rows
    rows = cascade_orders(build_config(args), load_pairs(args.pairs), load_ideas(args.ideas))
    _table(rows, ["order", "TP", "FP", "FN", "precision", "recall", "f1"])
    write_rows(Path(args.out_dir) / "cascade_orders.csv", rows)


def cmd_calibrate(args):
    from .evaluation import calibrate, write_rows
    cfg = build_config(args)
    c = calibrate(cfg, args.term_pairs)
    best = {}
    for m, res in c["matchers"].items():
        print(f"\n{m}")
        _table(res, ["threshold", "f1_train", "f1_test"])
        top = max(res, key=lambda e: (e["f1_train"], -abs(e["threshold"] - cfg["thresholds"][m])))
        best[m] = top["threshold"]
        print(f"  best on train: {top['threshold']} (train F1 {top['f1_train']}, held-out F1 {top['f1_test']}); "
              f"configured: {cfg['thresholds'][m]}")
    write_rows(Path(args.out_dir) / "calibration_scores.csv", c["scores"])
    if args.apply:
        path = Path(args.apply)
        new = load_config(getattr(args, "config", None)); new["thresholds"].update(best)
        path.write_text(json.dumps(new, indent=2), encoding="utf-8")
        print(f"\nwrote calibrated config {path} (use it with --config {path})")


def cmd_rules(args):
    from .rules import as_table
    rows = [r for r in as_table() if (not args.case or r["case"] == args.case) and (not args.pattern or r["pattern"] == args.pattern)]
    for r in rows:
        print(f"{r['rule_id']}  {r['pattern']:<4} {r['case']:<5} -> {r['output']}")
        print(textwrap.indent(textwrap.fill(f"if: {r['condition']}", 90), "      "))
        print(textwrap.indent(textwrap.fill(f"e.g. {r['example']}", 90), "      "))
    print(f"\n{len(rows)} rules")


def cmd_segment(args):
    """Step 1: split free text into WHAT/HOW/WHEN, or score the segmenters against data/ideas.csv."""
    from .segmentation import evaluate_segmenter, segment
    cfg = build_config(args)
    if args.text:
        for k, v in segment(args.text, args.segmenter or "syntax", cfg).items():
            print(f"{k.upper():<5}: {v}")
        return
    from .evaluation import load_ideas, write_rows
    ideas = load_ideas(args.ideas)
    for m in ([args.segmenter] if args.segmenter else ["simple", "syntax"]):
        r = evaluate_segmenter(ideas, m, cfg)
        print(f"{m:<8} scored on {r['n_scored']}/{r['n_ideas']} ideas  token-F1 WHAT {r['f1']['what']}  HOW {r['f1']['how']}"
              f"  WHEN {r['f1']['when']}   (share with F1>=0.8: {r['f1_at_least_0.8']})")
        write_rows(Path(args.out_dir) / f"segmentation_{m}.csv", r["rows"])
    print("Ideas whose manual WHAT/HOW cannot be derived from their text are not scored (gold_derivable = False).")


def cmd_check(args):
    from .resources import check
    ok = check(build_config(args))
    sys.exit(0 if ok else 1)


def cmd_serve(args):
    import uvicorn
    print(f"Web interface: http://{args.host}:{args.port}")
    uvicorn.run("backend.app:app", host=args.host, port=args.port, app_dir=str(ROOT), reload=False)


# ------------------------------------------------------------------ parser
def main(argv=None):
    ap = argparse.ArgumentParser(prog="idearel", description="Interpretable detection of relationships between ideas")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--config", help="configuration file (default config/default.json)")
    common.add_argument("--set", action="append", metavar="KEY=VALUE", help="override an option, e.g. thresholds.content=0.8")
    common.add_argument("--extractor", choices=["spacy", "heuristic", "corenlp", "adelie", "ollama"])
    common.add_argument("--segmenter", choices=["simple", "syntax", "ollama"], help="Step 1 for free-text ideas")
    data = argparse.ArgumentParser(add_help=False)
    data.add_argument("--ideas", default=str(ROOT / "data" / "ideas.csv"))
    data.add_argument("--pairs", default=str(ROOT / "data" / "pairs.csv"))
    data.add_argument("--out-dir", default=str(ROOT / "results"))
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("compare", parents=[common], help="relationship between two ideas")
    for k in ("what1", "how1", "what2", "how2", "idea1", "idea2"):
        p.add_argument(f"--{k}")
    p.add_argument("--json", action="store_true"); p.add_argument("--quiet", action="store_true")
    p.set_defaults(func=cmd_compare)

    p = sub.add_parser("extract", parents=[common], help="show the elements of one idea")
    p.add_argument("--what"); p.add_argument("--how"); p.set_defaults(func=cmd_extract)

    p = sub.add_parser("batch", parents=[common], help="all pairs of an idea file (or the pairs of a pair file)")
    p.add_argument("--ideas", required=True); p.add_argument("--pairs"); p.add_argument("--out", default="results/batch.csv")
    p.set_defaults(func=cmd_batch)

    for name, f, h in (("evaluate", cmd_evaluate, "metrics on the 240 annotated pairs"),
                       ("ablation", cmd_ablation, "all 15 matcher subsets"),
                       ("orders", cmd_orders, "all orders of the cascade")):
        p = sub.add_parser(name, parents=[common, data], help=h); p.set_defaults(func=f)

    p = sub.add_parser("calibrate", parents=[common], help="threshold sweep on the 172 term pairs")
    p.add_argument("--term-pairs", default=str(ROOT / "data" / "term_pairs.csv"))
    p.add_argument("--out-dir", default=str(ROOT / "results"))
    p.add_argument("--apply", metavar="FILE", help="write a config with the thresholds that are best on the train split")
    p.set_defaults(func=cmd_calibrate)

    p = sub.add_parser("rules", help="list the 54 rules of the paper"); p.add_argument("--case")
    p.add_argument("--pattern", choices=["WHAT", "HOW"])
    p.set_defaults(func=cmd_rules)

    p = sub.add_parser("segment", parents=[common], help="Step 1: split free text into WHAT/HOW/WHEN, or evaluate the segmenters")
    p.add_argument("--text"); p.add_argument("--ideas", default=str(ROOT / "data" / "ideas.csv"))
    p.add_argument("--out-dir", default=str(ROOT / "results")); p.set_defaults(func=cmd_segment)

    p = sub.add_parser("check", parents=[common], help="check that the local resources are installed"); p.set_defaults(func=cmd_check)

    p = sub.add_parser("serve", help="start the web version"); p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000); p.set_defaults(func=cmd_serve)

    args = ap.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
