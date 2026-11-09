"""Run the zero-shot pair classification through an API (alternative to the chat apps used for the reported runs).

    python experiments/03_llm_pair_classification/run_llm_api.py --provider openai    --model gpt-4o           --condition raw_text
    python experiments/03_llm_pair_classification/run_llm_api.py --provider anthropic --model claude-sonnet-5-5 --condition what_how
    python experiments/03_llm_pair_classification/run_llm_api.py --provider google    --model gemini-2.5-flash  --condition definitions --run R2

The reported runs (outputs/*.csv, sheet 04) were made in chat (GPT-4o in the ChatGPT app) with the prompts in
prompts/. An API run asks the same question for each pair, one call per pair, so its labels can differ from the
reported runs; keep its output separate and score it with score_llm.py.

Conditions and inputs (inputs/):
  raw_text     raw_text_240.csv            prompt prompts/raw_text_per_pair.txt
  what_how     what_how_240_as_run.csv     same prompt, 'WHAT. HOW' as the idea text (--sheet01: with the IDEA003/IDEA020 patterns of sheet 01)
  definitions  what_how_240_definitions.csv  same prompt, preceded by the definitions of prompts/what_how_definitions_file.txt

The key is read from OPENAI_API_KEY / ANTHROPIC_API_KEY / GEMINI_API_KEY, or asked for (never saved).
Output: outputs/api_<model>_<condition>_<run>.csv (Pair_ID, label, raw answer). Safe to stop and restart.
Needs: pip install openai | anthropic | google-genai
"""
import argparse
import getpass
import os
import sys
import time
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from common import norm_label  # noqa: E402

QUESTION = (HERE / "prompts" / "raw_text_per_pair.txt").read_text(encoding="utf-8").strip()
DEFS = (HERE / "prompts" / "what_how_definitions_file.txt").read_text(encoding="utf-8")
# the definitions part of the file prompt, without the file and output instructions
DEFS = DEFS[DEFS.index("Every idea answers"):DEFS.index("Rules:")].strip()


def load_pairs(condition, sheet01):
    if condition == "raw_text":
        d = pd.read_csv(HERE / "inputs" / "raw_text_240.csv")
    elif condition == "what_how":
        d = pd.read_csv(HERE / "inputs" / ("what_how_240_sheet01.csv" if sheet01 else "what_how_240_as_run.csv"))
    else:
        w = pd.read_csv(HERE / "inputs" / "what_how_240_definitions.csv").fillna("")
        j = lambda a, b: ". ".join(t.strip().rstrip(".") for t in (a, b) if t.strip())
        d = pd.DataFrame(dict(Pair_ID=w.Pair_ID, Idea1=[j(a, b) for a, b in zip(w.Idea1_WHAT, w.Idea1_HOW)],
                              Idea2=[j(a, b) for a, b in zip(w.Idea2_WHAT, w.Idea2_HOW)]))
    return d


def prompt(condition, a, b):
    q = QUESTION.replace("[Idea1]", str(a).strip().rstrip(".")).replace("[Idea2]", str(b).strip().rstrip("."))
    return f"{DEFS}\n\n{q}" if condition == "definitions" else q


def client_for(provider, model, temperature):
    env = {"openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY", "google": "GEMINI_API_KEY"}[provider]
    key = os.environ.get(env) or getpass.getpass(f"{env} (hidden, not saved): ").strip()
    kw = {} if temperature is None else {"temperature": temperature}
    if provider == "openai":
        from openai import OpenAI
        c = OpenAI(api_key=key)
        return lambda p: c.chat.completions.create(model=model, messages=[{"role": "user", "content": p}], **kw).choices[0].message.content
    if provider == "anthropic":
        import anthropic
        c = anthropic.Anthropic(api_key=key)
        return lambda p: c.messages.create(model=model, max_tokens=50, messages=[{"role": "user", "content": p}], **kw).content[0].text
    from google import genai
    c = genai.Client(api_key=key)
    cfg = {"temperature": temperature} if temperature is not None else None
    return lambda p: c.models.generate_content(model=model, contents=p, config=cfg).text


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--provider", choices=["openai", "anthropic", "google"], required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--condition", choices=["raw_text", "what_how", "definitions"], required=True)
    ap.add_argument("--run", default="R1", help="run name, e.g. R1 or R2 (separate output file)")
    ap.add_argument("--sheet01", action="store_true", help="what_how: use the IDEA003/IDEA020 patterns of sheet 01")
    ap.add_argument("--temperature", type=float, default=None, help="default: the provider's default, as in the apps")
    ap.add_argument("--dry-run", action="store_true", help="print the first prompt and stop")
    a = ap.parse_args()

    pairs = load_pairs(a.condition, a.sheet01)
    if a.dry_run:
        print(prompt(a.condition, pairs.Idea1[0], pairs.Idea2[0])); return
    out = HERE / "outputs" / f"api_{a.model.replace('/', '_')}_{a.condition}{'_sheet01' if a.sheet01 else ''}_{a.run}.csv"
    done = pd.read_csv(out).set_index("Pair_ID") if out.exists() else pd.DataFrame(columns=["label", "raw"])
    ask = client_for(a.provider, a.model, a.temperature)
    rows = [dict(Pair_ID=i, label=r.label, raw=r.raw) for i, r in done.iterrows() if r.label not in ("ERROR",)]
    todo = [r for r in pairs.itertuples() if r.Pair_ID not in {x["Pair_ID"] for x in rows}]
    print(f"{a.provider} {a.model} {a.condition} {a.run}: {len(todo)} of {len(pairs)} pairs to do")
    for n, r in enumerate(todo, 1):
        for attempt in range(5):
            try:
                txt = (ask(prompt(a.condition, r.Idea1, r.Idea2)) or "").strip(); break
            except Exception as e:  # rate limit or network: wait and retry
                print(f"  {r.Pair_ID}: {type(e).__name__}, retrying"); time.sleep(2 ** attempt * 3); txt = None
        rows.append(dict(Pair_ID=r.Pair_ID, label=norm_label(txt) if txt is not None else "ERROR", raw=txt or ""))
        if n % 20 == 0 or n == len(todo):
            pd.DataFrame(rows).to_csv(out, index=False); print(f"  {n}/{len(todo)}")
    print(f"written {out}\nscore it with: python {HERE / 'score_llm.py'} {out}")


if __name__ == "__main__":
    main()
