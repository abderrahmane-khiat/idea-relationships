# idearel v2: version 1 + oracle mode + refined rule set (future work)

**Version 2** contains everything in version 1 (`../v1`: the 54 rules of the paper, terminal and web interface) and adds: the **oracle mode** (elements given by a human instead of being extracted, `--oracle FILE`, and the *Oracle elements* panel of the web page), a **refined rule set** with the *unknown* outcome (`--rules v2`, see [RULES_V2.md](RULES_V2.md)), and the evaluation of Step 1 on free text. The 54 rules of the paper remain the default (`--rules v1`).

This is a reference implementation of the framework in the paper *Interpretable Detection of Multidimensional Relationships between Ideas in Crowd Ideation Platforms*.

Given two ideas, each described by a **WHAT** pattern (what the idea is) and a **HOW** pattern (how it works), the framework decides whether they are **duplicate**, **generalise/detail**, **alternative-solution**, **similar** or **disjoint**. It also explains each decision: which elements were extracted, which matcher linked which terms, with what score, and which of the 54 rules fired.

Everything runs locally. There is no external API and no API key.

There are two interfaces, and both use the same Python package (`src/idearel`):

| Interface | Start with | For |
|---|---|---|
| Terminal | `idearel compare ...`, `idearel evaluate`, ... | testing, batch runs, reproducing the experiments |
| Web | `idearel serve`, then open http://127.0.0.1:8000 | entering two ideas and seeing the relationship and the full audit trail |

---

## 1. Installation (about 5 minutes, once)

You need Python 3.9 or newer.

```bash
cd framework/v2                           # from the root of the repository
python -m venv .venv
# Windows:  .venv\Scripts\activate        Linux / macOS:  source .venv/bin/activate
pip install -r requirements.txt          # or requirements-lock.txt for the exact tested versions
pip install -e .                          # makes the `idearel` command available
python scripts/setup_resources.py         # WordNet, WordNet-IC, spaCy model, GloVe vectors (~200 MB)
idearel check                             # every line should say [ok]
```

If you skip `pip install -e .`, replace `idearel` with `python -m idearel` in every command below, and set `PYTHONPATH=src` first (`set PYTHONPATH=src` on Windows).

To check that everything works:

```bash
pytest                                     # 115 tests: rules v1 and v2, pipeline, web API
```

---

## 2. Terminal version

### Compare two ideas

```bash
idearel compare \
  --what1 "Window composed of heat-sensitive material" --how1 "indicates the exit path" \
  --what2 "Window made of heat-sensitive material"     --how2 "shows the exit path"
```

```
==============================================================================
RELATIONSHIP: DUPLICATE
Decided by:   W09 [T-T]: SRS VR ORS and same HOW (rule 1a)
HOW:          same  (rule H01)
==============================================================================
Step 2 - elements
  idea1 WHAT: triple <Window | composed of | heat-sensitive material>  [spacy]
  idea1 HOW : triple <Window | indicate | exit path>  [spacy]
  ...
Step 3 - links (cascade)
  'Window' ~ 'Window' -> equals  by structure
      structure    equals      score 1.0  same concept window.n.01
  'composed of' ~ 'made of' -> synonym  by linguistic
  ...
Step 4 - codes: case=T-T, HOW=same, S=SRS, V=VR, O=ORS
```

Options:

- Free text instead of patterns: `--idea1 "Rescue floor, that lights up to show the exit path" --idea2 "..."`. The text is split at the first comma or relative pronoun.
- `--json` prints the full decision as JSON; `--quiet` prints only the verdict.

### Other commands

| Command | What it does |
|---|---|
| `idearel extract --what "..." --how "..."` | Shows the elements of one idea (triple, single term or sequence of words) |
| `idearel batch --ideas my_ideas.csv --out results/batch.csv` | Compares all pairs of ideas in a CSV with columns `Idea_ID, Idea_Text, WHAT, HOW, WHEN`; `--pairs` limits it to listed pairs |
| `idearel evaluate` | Runs this implementation on the 240 annotated pairs and prints the Task 1 (binary) and Task 2 (five-way) metrics, next to those of the labels in the data file |
| `idearel ablation` | All 15 subsets of the four matchers |
| `idearel orders` | All 24 orders of the cascade |
| `idearel calibrate [--apply calibrated.json]` | Threshold sweep for each matcher on the 172 term pairs (train / held-out); `--apply` writes a config with the best train thresholds |
| `idearel rules [--case T-T] [--pattern HOW]` | Lists the 54 rules with their conditions and the paper's examples |
| `idearel oracle-template --out oracle.json` | Writes the extracted elements of every idea to an editable file for oracle mode |
| `idearel check` | Checks the local resources |
| `python scripts/benchmark.py` | Runtime at several dataset sizes, with and without the link cache; matcher calls, cache hits and hardware (`results/benchmark.csv`) |
| `python scripts/paper_examples.py [--oracle-types]` | Runs the 41 examples of Appendix B and shows which rule fires for each |
| `python scripts/tune.py [--rules v2]` | Grid search of the settings with nested cross-validation (`results/tuning/`; best configuration in `config/tuned.json`) |
| `idearel serve [--port 8000]` | Starts the web version |

Every command accepts:

- `--config FILE`
- `--set key=value` (repeatable), for example `--set thresholds.content=0.7` or `--set cascade.order=linguistic,structure,content,terminology`
- `--extractor spacy|heuristic|corenlp|adelie|ollama`
- `--oracle FILE`

Results are written to `results/`.

---

## 3. Web version

```bash
idearel serve            # or: start_web.bat (Windows), ./start_web.sh (Linux/macOS)
```

Open http://127.0.0.1:8000, then:

1. Type the WHAT and HOW of the two ideas, or load one of the 52 ideas of the dataset.
2. Optionally open **Oracle elements** to give the triple, single term or sequence of words yourself.
3. Optionally open **Settings** to choose the extractor, reorder or disable matchers (drag and drop), change the thresholds, or choose the variant of triple rule SD-VD-OD.
4. Click **Find the relationship**.

The page shows the verdict, the rule, the HOW decision, the four elements, every matcher call with its score and threshold, and the rule codes.

The backend is a FastAPI application (`backend/app.py`) with interactive API documentation at http://127.0.0.1:8000/docs.

| Endpoint | |
|---|---|
| `POST /api/compare` | `{"idea1": {"what": "...", "how": "..."}, "idea2": {...}, "options": {...}}` returns the decision with its audit trail |
| `POST /api/extract` | Elements of one idea |
| `GET /api/rules` | The 54 rules |
| `GET /api/examples` | The ideas in `data/ideas.csv` |
| `GET /api/health` | Status and default options |

The frontend (`frontend/`) is plain HTML, CSS and JavaScript with no build step.

---

## 4. How the code follows the paper

```
idea (WHAT, HOW, WHEN)
   │  Step 1  patterns: given by the structured interface, or split from free text  (text.split_free_text)
   ▼
   │  Step 2  element identification                                        src/idearel/extraction/
   │          triple <S,P,O> | single term (W) | sequence of words (SW)
   ▼
   │  Step 3  linking: cascade of matchers                                  src/idearel/matching/
   │          structure → linguistic → content → terminology (first conclusive wins)
   ▼
   │  Step 4  13 HOW rules decide "same HOW", then 41 WHAT rules            src/idearel/rules/
   ▼
relationship + rule + full audit trail                                      src/idearel/models.Decision
```

```
idearel/
├── src/idearel/            framework (Python package)
│   ├── models.py           Idea, Element, Link, MatcherCall, Decision, Relationship
│   ├── pipeline.py         Framework: extraction → cascade → rules
│   ├── extraction/         spacy, heuristic, corenlp, adelie, ollama, oracle
│   ├── matching/           four matchers + cascade
│   ├── rules/              catalog.py (54 rules, Appendix B) + engine.py
│   ├── evaluation.py       metrics, ablation, cascade orders, calibration
│   ├── resources.py        resource check / download
│   └── cli.py              terminal version
├── backend/app.py          web version: API (FastAPI)
├── frontend/               web version: index.html, app.js, style.css
├── config/default.json     every option (thresholds, cascade, extractor, ...)
├── config/lexicon.json     optional domain synonym groups for the linguistic matcher
├── data/                   ideas, 240 annotated pairs, 172 term pairs, oracle files (exported from ../../data)
├── scripts/                setup_resources.py, export_data.py, paper_examples.py
└── tests/                  test_rules.py (all 54 rules), test_pipeline.py, test_api.py
```

### Step 2: element identification and local alternatives to OpenIE

| `extractor` | What it is | Needs |
|---|---|---|
| `spacy` (default) | Triples from the dependency parse (subject, predicate with particles and prepositions, object) | `en_core_web_md` |
| `corenlp` | Stanford OpenIE, as in the paper, through a local CoreNLP server | Java + CoreNLP 4.5.x: `java -mx4g -cp "*" edu.stanford.nlp.pipeline.StanfordCoreNLPServer -port 9000` |
| `adelie` | ADELIE, an open LLM fine-tuned for information extraction (THU-KEG), run locally with HuggingFace | `pip install transformers torch accelerate`; about 6 GB (3B model) |
| `ollama` | Any local LLM served by Ollama (for example Llama 3.1) | Ollama running locally: `ollama pull llama3.1` |
| `heuristic` | Pure-Python fallback with NLTK part-of-speech tags | nothing extra |
| oracle (`--oracle FILE`) | Elements given by a human (Reviewer 1, comment 7) | a JSON file, see below |

If the configured extractor fails (for example, the CoreNLP server is not running), the `extractor_fallback` is used and the decision says so in its notes.

A pattern without a triple is classified as a **single term** (no verb and at most 4 words) or a **sequence of words**.

With `implicit_how_subject: true` (the default), a HOW written without a subject ("indicates the exit path", "that lights up ...") takes the head of the WHAT as its subject. This matches the HOW triples in the paper, such as *Window indicates path of exit*.

### Oracle mode

```json
{
  "IDEA020": {
    "WHAT": {"type": "single_term", "text": "rescue indication floor"},
    "HOW":  {"type": "triple", "subject": "floor", "predicate": "lights up to show", "object": "exit path"}
  }
}
```

Ideas or patterns that are missing from the oracle file fall back to the extractor, so a partial oracle is possible.

`idearel oracle-template` writes the extracted elements of all ideas so that they can be corrected by hand. `data/oracle_study4.json` holds the expert-validated elements of the Study 4 ideas.

To measure how extraction errors affect the result, compare:

```bash
idearel evaluate --out-dir results/extracted
idearel evaluate --oracle oracle.json --out-dir results/oracle
```

### Step 3: the four matchers and the cascade

| Matcher | Paper | This implementation (local) | Threshold |
|---|---|---|---|
| structure | Knowledge-graph subclass / sameAs | `wordnet`: noun hypernym hierarchy (default); `sparql`: Wikidata P279 on a local endpoint; `taxonomy`: your JSON taxonomy `{"term": ["parent", ...]}` | (no score) |
| linguistic | Lin similarity on WordNet | Lin with Brown information content, shared WordNet sense, antonyms for predicates, optional domain lexicon | 0.75 |
| content | Word2Vec cosine | Cosine of averaged word vectors: GloVe (default), any word2vec/GloVe file (`content.vectors_file`), `word2vec-google-news-300`, or spaCy vectors | 0.80 |
| terminology | Levenshtein | Normalised Levenshtein similarity | 0.85 |

- The cascade runs the matchers in `cascade.order` and stops at the first conclusive one. The audit trail keeps every call.
- The structure matcher is not applied to predicates or to sequences of words.
- Sequences of words are compared with the content and terminology matchers.
- `cascade.enabled` switches matchers off (ablation).

### Step 4: the 54 rules (Appendix B)

`src/idearel/rules/catalog.py` lists every rule with its ID, case, condition, output and the example from the paper:

- **W01–W41:** WHAT rules (T-W 4, T-SW 4, T-T 17, W-W 8, W-SW 4, SW-SW 4).
- **H01–H13:** HOW rules (T-T 8, then one each for T-W, T-SW, W-W, W-SW, SW-SW).

Codes (Table 1):

| Code | Meaning |
|---|---|
| SRS / ORS | same subject / object (equals or synonym) |
| SR / OR | related (similar, subclass, superclass) |
| SD / OD | no link |
| VR | predicates are equal, synonym or similar |
| VD | predicates have no link or are antonyms |

`tests/test_rules.py` checks every combination of codes against the rule tables, so the rule logic is verified independently of the language resources.

Decisions and options in the rule engine:

- **SD-VD-OD with the same HOW:** Appendix B (rule 8a) says *alternative-solution*, while Algorithm 1 gives *disjoint*. The default follows the appendix; `--set rules.sd_vd_od=algorithm1` gives Algorithm 1.
- **Generalise/detail direction:** the more specific idea *details* the more general one, and the output states the direction ("IDEA1 details IDEA2").
- **Pair order:** the engine puts the two elements in a canonical order (triple, then single term, then sequence of words), so the result does not depend on which idea comes first.
- **Missing WHAT:** if an idea has no WHAT, the default applies: *disjoint* (no relation evidence found).

### Privacy

After the one-time download of the resources (`scripts/setup_resources.py`), no idea text leaves your machine:
- WordNet, the word vectors, spaCy and the optional ADELIE model run in-process;
- CoreNLP and Ollama run as local servers;
- the optional SPARQL backend points to a local endpoint by default (`structure.sparql_endpoint = http://localhost:9999/...`).

If you configure a public endpoint instead, the terms compared by the structure matcher are sent to that endpoint.

---

## 4b. Version 2 for future work: refined rule set, *unknown*, and Step 1 for free text

- **Refined rule set:** `--rules v2` (web: **Settings → Rule set**) replaces the 41 WHAT rules by one decision table, uses three HOW levels, and adds the *unknown* outcome (abstain on missing or weak evidence, rules U01–U04). The rule set and its relation to the 54 rules are described in [RULES_V2.md](RULES_V2.md). Version 1 stays the default and is unchanged.
- **Free text:** `idearel segment --text "..."` splits free text into WHAT/HOW/WHEN (`--segmenter syntax`: spaCy-based; `ollama`: local LLM, falls back to syntax). On the web page, use **Start from free text** in each idea.
- **Scoring Step 1:** `idearel segment` alone scores the segmenters against the manual patterns of `data/ideas.csv`.

## 5. Data

| File | Content |
|---|---|
| `../../data/idea_relationships_data.xlsx` | Full release workbook (all sheets, reviewer-tagged), at the root of the repository |
| `data/ideas.csv` | The 52 ideas with WHAT / HOW / WHEN |
| `data/pairs.csv` | The 240 annotated pairs: annotators A/B/C, `Human_Majority` (the reference), the original `System_Label` |
| `data/term_pairs.csv` | The 172 calibration term pairs (train 138 / held-out 34) with the original matcher scores |
| `data/oracle_study4.json` | Expert-validated elements of the Study 4 ideas |
| `data/oracle_ideas.json` | Draft oracle elements for the 52 test ideas (not yet verified by the authors) |

`python scripts/export_data.py` regenerates the CSV files from the workbook.

---

## 6. Troubleshooting

| Problem | Fix |
|---|---|
| `LookupError: wordnet` | `python scripts/setup_resources.py` |
| spaCy model missing | `python -m spacy download en_core_web_md`, or `--extractor heuristic` |
| First call slow (5–20 s) | Loading WordNet and the word vectors; later calls take milliseconds |
| `corenlp failed (URLError)` in the notes | Start the CoreNLP server (section 4); until then the heuristic extractor is used |
| Port 8000 in use | `idearel serve --port 8080` |
| Behind a proxy, NLTK downloads fail | Download the NLTK data manually (https://www.nltk.org/data.html) into `~/nltk_data` |

## License

MIT (see `LICENSE`). For the data, see the README at the root of the repository.
