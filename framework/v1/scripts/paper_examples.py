"""Run the framework on the 41 WHAT-rule examples of Appendix B and report which rule fires.

    python scripts/paper_examples.py

The rule logic itself is verified exhaustively in tests/test_rules.py.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from idearel import Framework, Idea, load_config  # noqa: E402
from idearel.models import Element, ElementType  # noqa: E402
from idearel.rules.catalog import WHAT_RULES  # noqa: E402

TYPES = {"T": ElementType.TRIPLE, "W": ElementType.TERM, "SW": ElementType.SW}


def parse(s):
    m = re.match(r"(.*?)\s*\((.*)\)\s*$", s.strip())
    return m.group(1), m.group(2)


def main():
    fw = Framework(load_config())
    ok = 0
    for rid, case, cond, out, ex in WHAT_RULES:
        (w1, h1), (w2, h2) = (parse(x) for x in ex.split(" / "))
        t1, t2 = case.split("-")
        f = fw
        d = f.compare(Idea("I1", "", w1, h1), Idea("I2", "", w2, h2))
        good = d.rule_id == rid
        ok += good
        print(f"{'OK ' if good else '-- '} {rid} {case:<5} expected {out.value:<20} got {d.rule_id} {d.relationship.value:<20} "
              f"{ {k: v for k, v in d.codes.items() if not k.startswith('HOW_')} }")
    print(f"\n{ok}/{len(WHAT_RULES)} examples reach the rule given in the paper")


if __name__ == "__main__":
    main()
