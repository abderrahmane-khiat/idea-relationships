# Interpretable Detection of Multidimensional Relationships between Ideas in Crowd Ideation Platforms

Code, data and experiments of the paper (revised manuscript, JJCIT). Given two ideas described by **WHAT** (what
the idea is), **HOW** (how it works) and **WHEN**, the framework decides whether they are *duplicate*,
*generalise/detail*, *alternative solution*, *similar* or *disjoint*, and explains every decision: the extracted
elements, the matcher that linked each pair of terms, and the rule that fired (54 rules).

```
data/idea_relationships_data.xlsx   all data: ideas, 240 annotated pairs, outputs of every method, prompts, results
evaluate.py                         recomputes every reported metric and test from the raw data columns
evaluate_output.csv                 output of evaluate.py for this release
framework/v1/                       the framework of the paper: 54 rules, terminal and web interface
framework/v2/                       version 1 + oracle mode + refined rule set (future work of the paper)
experiments/                        inputs, prompts, outputs and scripts behind every computed value of the workbook
sparql/                             SPARQL queries of the structure-based matcher (Appendix A)
```

## Quick start

**Recompute the results of the paper** (a few seconds; no model, no API key):

```bash
pip install -r requirements.txt
python evaluate.py                       # reads data/idea_relationships_data.xlsx, writes evaluate_output.csv
```

**Run the framework on your own ideas**, in the terminal or in the browser:

```bash
cd framework/v1
pip install -r requirements.txt && pip install -e .
python scripts/setup_resources.py        # WordNet, spaCy model, GloVe vectors (once, about 200 MB)
idearel compare --what1 "Window composed of heat-sensitive material" --how1 "indicates the exit path" \
                --what2 "Window made of heat-sensitive material"     --how2 "shows the exit path"
idearel serve                            # web interface at http://127.0.0.1:8000
```

On Windows, `start_web.bat` starts the web interface. Details: [`framework/v1/README.md`](framework/v1/README.md).

**Rerun an experiment** (SBERT, TF-IDF, LLM prompts, triple extraction, sampling, screening): see
[`experiments/README.md`](experiments/README.md). Each script prints `[same]` when its result equals the workbook.

## Two versions of the framework

| | `framework/v1` | `framework/v2` |
|---|---|---|
| Purpose | the framework as described in the paper | version 1 plus the tools of the future work (Section 10) |
| Rules | the 54 rules of Appendix B | the 54 rules, or a refined rule set with an explicit *unknown* output (`--rules v2`, see `RULES_V2.md`) |
| Elements | extracted (spaCy by default; CoreNLP OpenIE, ADELIE, Ollama, heuristic) | extracted, or given manually (**oracle mode**, `--oracle`), to measure the rules with perfect elements |
| Interfaces | terminal (`idearel ...`) and web (`idearel serve`) | the same, with the oracle and rule options in both |
| Tests | 94 | 115 |

Both versions run fully locally: no external API and no API key.

**Prototype and released implementation.** The labels of our approach reported in the paper (sheet 02) were
produced by the prototype used in the studies (Stanford CoreNLP 4.5.5 OpenIE, WordNet 3.1, Word2Vec, DBpedia
Spotlight 1.1 and local copies of DBpedia and Wikidata). `framework/` implements the same pipeline and rules with
local resources that need no server (spaCy, WordNet through NLTK, GloVe); its `corenlp` extractor and `sparql`
structure backend connect it to the resources of the prototype. The reported results are recomputed from the
released outputs by `evaluate.py` and the experiment scripts.

## Where each table of the revised manuscript comes from

| Table | Content | Workbook sheet | Recomputed by |
|---|---|---|---|
| 5 | Task 1, our approach | 05 | `evaluate.py` |
| 6, 7 | Task 2, confusion matrix and per-class metrics | 06 | `evaluate.py` |
| 8 | Rule coverage | 09 | `evaluate.py` |
| 9 | Relations detected per category | 07 | `evaluate.py` |
| 10 | Task 1, all methods | 05 (outputs in 04) | `evaluate.py`; outputs from `experiments/01_sbert`, `02_tfidf`, `03_llm_pair_classification` |
| 11 | Task 2, macro metrics of our approach and the LLMs | 06 | `evaluate.py`, `experiments/03_llm_pair_classification/score_llm.py` |
| 12 | Threshold sweep of the similarity baselines | 08 | `evaluate.py`, `experiments/02_tfidf/run_tfidf.py` |
| 13 | Our approach vs Dandelion | 07 | `evaluate.py` |
| 14 | Study 3 (effect sizes, equivalence tests) | 14 | formulas from the reported means, SDs and group sizes |
| 15 | Element identification (triple rows) | 13 | `evaluate.py`, `experiments/04_triple_extraction/score_extraction.py` |
| 16-18 | Standalone matchers per term type | 12 (scores in 10) | `evaluate.py` (structure-based rows kept from the original evaluation) |
| 19 | Matcher F-measure on the calibration term pairs | 11 (scores in 10) | `evaluate.py` |
| 20, 21 | Matcher ablation, cascade orders | 12 | `evaluate.py` |
| 23 | Upper bound with perfect extraction | 02 | `evaluate.py` |
| 24 | Runtime of the released implementation | 21 | `framework/v1/scripts/benchmark.py` |

Also recomputed by `evaluate.py`: the significance tests of Section 7.4 (sheet 16), annotator agreement
(sheet 06), the stratified estimate of Section 6.5 (sheet 23), the LLM error analysis of Section 7.5 (sheet 22),
the candidate screening of Section 9.6 (sheet 20) and the optional ADELIE check of the response letter (sheet 24).
Tables 1-4 hold definitions and examples. Table 22 (term recognition) and the sequence-of-words and single-term
rows of Table 15 are kept from the original evaluation; the workbook does not hold them at pair level.

**Table numbers in sheet names.** Sheet names such as `07_Counts_T6_T8` or `11_Calibration_T14` use the table
numbers of the first submission. In the revised manuscript, former Tables 5-15 are Tables 5, 9, 10, 13, 14, 15,
16, 17, 18, 19 and 22; the new tables are 6 (confusion matrix), 7 (per-class results), 8 (rule coverage),
11 (five-way macro results), 12 (threshold sweep), 20 (matcher ablation), 21 (cascade order), 23 (upper bound)
and 24 (runtime).

## The data workbook

`data/idea_relationships_data.xlsx` has an index (`00_Index_Reviewer_Map`) and a dictionary of every column
(`00_Column_Dictionary`). Result sheets are live formulas on the data sheets; `evaluate.py` recomputes them
independently from the raw data columns. Sheet names end with the reviewer comments they answer
(`R1-4` = Reviewer 1, comment 4).

| Sheet | Content | Manuscript |
|---|---|---|
| `01_Ideas_R2-4` | The 52 ideas of the test pairs with WHAT / HOW / WHEN (written by the participants, validated by experts) | §5, §7.1 |
| `02_Test_Pairs_R1-1_R1-2_R3-9` | The 240 test pairs: annotators A/B/C, majority (reference), label, rule, branch and matched terms of our approach, rank band | §6, Tables 5-8 |
| `03_Sampling_R3-1` | Population of 4,465 pairs with Dandelion ranks, rank bands, sampled pairs | §6.1 |
| `04_Baseline_Outputs_R2-4_R3-7` | Pair-level output of every baseline: Dandelion, SBERT (3 inputs), TF-IDF, GPT-4o (raw, WHAT+HOW, with definitions), Claude Sonnet 5.5, Gemini 2.5 Flash | §7.1, Tables 9-12 |
| `05_Binary_Metrics_R1-1_R2-4` | TP, FP, FN, TN, precision, recall, F1, accuracy per method | Tables 5, 10 |
| `06_Multiclass_R1-2_R1-9` | Confusion matrix, per-class and macro metrics, GPT-4o run-to-run kappa, Fleiss' kappa, Krippendorff's alpha | §6.2, Tables 6, 7, 11 |
| `07_Counts_T6_T8_R1-1_R1-9` | Labels per method including the human reference; cross-tabulation with Dandelion | Tables 9, 13 |
| `08_Threshold_Sweeps_R1-5_R3-3` | P/R/F1 of SBERT, Dandelion and TF-IDF over thresholds 0.05-0.95 | Table 12 |
| `09_Rule_Coverage_R1-4_R3-5` | Pairs decided by each rule vs the default; F1 without the default | Table 8, §4.4 |
| `10_Calibration_Data_R1-5_R3-2` | 172 term pairs x 3 matchers: score, gold label, train/test split | §4.3.3, §9.4 |
| `11_Calibration_T14_R1-5_R3-2` | F1 per matcher and threshold for all, train and test term pairs | Table 19 |
| `12_Matchers_T11-13_R1-7` | Standalone matchers per term type, matcher ablation, cascade orders | Tables 16-18, 20, 21 |
| `13_Extraction_R1-7_R2-5_R3-8` | 70 WHAT/HOW phrases: Stanford OpenIE vs GPT-4o, expert flags, judgements | Table 15, §9.5 |
| `14_Study3_R1-6` | ANOVA, Hedges' g, confidence intervals, equivalence tests (TOST) | Table 14, §8 |
| `15_Generalise_Check_R1-3_R1-9` | Blind three-annotator check of the two pairs labelled generalise by our approach | §6.5 |
| `16_Significance_R1-2_R2-4_R3-3` | Paired-bootstrap F1 differences, exact McNemar (related pairs), McNemar (accuracy) | §7.4 |
| `17_LLM_Prompts_R2-4_R3-7_R3-8` | Exact prompts, models and dates of every LLM run | §7.1 |
| `18_Metadata` | Study facts, definitions, hardware, software versions, knowledge sources | §5, data availability |
| `20_Screening_R1-8` | Candidate screening by shared content words | §9.6 |
| `21_Runtime_R1-8` | Runtime at several dataset sizes, caching, matcher calls, hardware, extrapolation | Table 24, §9.6 |
| `22_LLM_Errors_R2-5` | False positives of every LLM run by label, shared content words and SBERT similarity | §7.5 |
| `23_Stratified_F_R3-1` | F-measure per Dandelion rank band and population-weighted estimate | §6.5 |
| `24_ADELIE_Optional_R3-8` | Optional: ADELIE triples of the 52 test ideas and an exploratory relatedness test | response letter only |

### Where each reviewer comment is answered in the data

| Comment | Topic | Sheets |
|---|---|---|
| R1-1 | Reproducible Tables 5-10, TP/FP/TN/FN, metric definitions, released data | 02, 04, 05, 06, 07, 18 |
| R1-2 | Blind multiclass annotation, confusion matrix, per-class metrics, multi-rater agreement | 02, 06 |
| R1-3 | Direction of generalise/detail | 15, 18 |
| R1-4 | Disjoint as "no evidence", coverage vs accuracy, default of Algorithm 1 | 09 |
| R1-5 | Calibration data separate from test, comparable tuning for the baselines | 08, 10, 11, 16 |
| R1-6 | Study 3: participants, time, diversity, effect sizes, equivalence | 14, 18 |
| R1-7 | Extraction errors, standalone matchers, ablation, cascade order | 12, 13 |
| R1-8 | Number of pairs and candidate screening, hardware, runtime, caching, local knowledge sources, software versions, release | 18, 20, 21 |
| R1-9 | Human label counts and per-class metrics; generalise check | 06, 07, 15 |
| R2-4 | SBERT and GPT-4o on raw text and on WHAT+HOW | 04, 05, 16, 17 |
| R2-5 | Extraction quality, LLM extractor, LLM scores and error analysis, GPT-4o with definitions | 04, 05, 06, 07, 13, 16, 17, 22 |
| R3-1 | Sampling design and rank bands | 03, 23 |
| R3-2 | Thresholds calibrated on a held-out term-pair split | 10, 11 |
| R3-3 | Dandelion kept as a historical baseline; SBERT and TF-IDF added with sweeps | 04, 05, 08, 16 |
| R3-5 | Default rule and F-measure without it | 09 |
| R3-7 | GPT-4o, Claude Sonnet 5.5, Gemini 2.5 Flash | 04, 05, 06, 16, 17 |
| R3-8 | Recent extractor vs Stanford OpenIE | 13, 24 |
| R3-9 | Multiclass re-annotation | 02, 06 |
| R2-1, R2-2, R2-3, R3-4, R3-6, R3-10 | Text-only changes | manuscript |

## Definitions

- **Reference label:** majority of three annotators (system label hidden, five labels offered). Related = any
  label except disjoint.
- **Task 1 (binary):** precision = TP/(TP+FP), recall = TP/(TP+FN), F1 = harmonic mean.
- **Task 2 (five-way):** macro = unweighted mean over the four classes with human labels (disjoint,
  alternative-solution, similar, duplicate); generalise/detail has no human case in the test set and is not scored.
- **Default rule:** when no rule fires, the output is disjoint (RuleID `else-default`): no relation evidence found.
- **Matcher thresholds:** linguistic 0.75, content 0.80, terminology 0.85; the structure-based matcher has no
  threshold. They were calibrated on the term-pair train split, not on the 240 test pairs.
- **Rank bands:** smallest Dandelion similarity rank of the two ideas: A 1-5, B 6-30, C 31-79, D 80 or more.

## Models and runs

| Method | Version and date | Input |
|---|---|---|
| Dandelion API | scores collected in the original study (API discontinued in 2023) | raw text |
| SBERT | `sentence-transformers/all-mpnet-base-v2`, cosine >= 0.75 | raw text; WHAT+HOW concatenation; mean of WHAT and HOW cosines |
| TF-IDF | scikit-learn `TfidfVectorizer` (English stop words, sublinear tf) fitted on the 52 idea texts | raw text |
| GPT-4o | ChatGPT app, October 2026, two runs per condition (WHAT+HOW runs in fresh chats); with definitions: 8 November 2026, two fresh chats | raw text; WHAT+HOW; WHAT+HOW with definitions |
| Claude Sonnet 5.5 | October 2026, one run | raw text |
| Gemini 2.5 Flash | October 2026, one run | raw text |
| GPT-4o extractor | ChatGPT app, October 2026 | 70 WHAT/HOW phrases |
| ADELIE (optional) | run by the authors on the 52 idea texts | raw text |

## Known limitations of the data

- Sheet 14 recomputes the Study 3 statistics from the reported means, SDs and group sizes.
- The test set contains one duplicate pair and no generalise/detail pair.
- No pair from rank band C (ranks 31-79) was sampled.
- 9 of the 24 identified ideas of the calibration data also occur among the 52 test ideas (ideas, not labels,
  overlap).
- For 11 pairs, the WHAT+HOW input of the GPT-4o WHAT+HOW runs and of the SBERT WHAT+HOW scores used an earlier
  version of the IDEA003 and IDEA020 patterns; these pairs are flagged in sheet 04 (column P), and the exact inputs
  are in `experiments/`.
- The GPT-4o extractor judgements (sheet 13) are single-rater judgements; strict and lenient rules are both
  reported.

## Environment of the original studies

Intel Core i7, 16 GB RAM, Windows. Stanford CoreNLP 4.5.5 (OpenIE), Princeton WordNet 3.1, Word2Vec, DBpedia
Spotlight 1.1, Blazegraph 2.1.5 (DBpedia release 2022-12), Wikidata Query RDF 0.3.137 (Wikidata dump 20230607);
all knowledge sources deployed locally. About 40 minutes for the 240 test pairs.

## License

Code (`evaluate.py`, `framework/`, `experiments/*.py`): MIT, see [`LICENSE`](LICENSE).
Data (`data/`, and the inputs and outputs under `experiments/`): Creative Commons Attribution 4.0 (CC BY 4.0).

## Citation

If you use this material, please cite the paper *Interpretable Detection of Multidimensional Relationships between
Ideas in Crowd Ideation Platforms* (Jordanian Journal of Computers and Information Technology, under review).
