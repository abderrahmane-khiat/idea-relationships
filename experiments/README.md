# Experiments: inputs, prompts, outputs and scripts behind the data workbook

Every value of `data/idea_relationships_data.xlsx` that is not a human annotation comes from one of the folders
below. Each folder holds the exact input, the prompt (for the LLMs), the reported output, and a script that
recomputes it or scores it. Scripts run from the repository root and print `[same]` when their result equals the
workbook.

```bash
pip install -r requirements.txt            # at the repository root
python experiments/build_inputs.py         # regenerates the input files from the workbook (identical to the ones here)
python experiments/export_outputs.py       # regenerates the reported outputs/ files from the workbook
```

| Folder | Workbook | Manuscript | Script | Reruns without the original setup? |
|---|---|---|---|---|
| `01_sbert` | sheet 04, F-H | Tables 9, 10, 12 | `run_sbert.py` | yes (downloads the model) |
| `02_tfidf` | sheet 04, I, S, T | Baseline 5, Tables 9, 10, 12 | `run_tfidf.py` | yes, identical values |
| `03_llm_pair_classification` | sheet 04, J-O, Q-R; sheet 17 | Tables 9, 10, 11; Section 7.5 | `score_llm.py`, `run_llm_api.py` | scoring: identical; new LLM runs give new labels |
| `04_triple_extraction` | sheet 13 | Table 15, Section 9.5 | `score_extraction.py` | scoring: identical |
| `05_adelie_optional` | sheet 24 | response letter only | `score_adelie.py` | scoring: identical |
| `06_sampling_strata` | sheets 03, 23 | Sections 6.1, 6.5 | `sampling_pattern.py` | yes, identical |
| `07_candidate_screening` | sheet 20 | Section 9.6 | `screening.py` | yes, identical |
| `08_runtime` | sheet 21, part B | Table 24, Section 9.6 | `framework/v1/scripts/benchmark.py` | yes (times depend on the machine) |

Everything else is recomputed from the workbook by `evaluate.py` at the repository root: binary and five-way
metrics, agreement, significance tests, rule coverage, the stratified estimate (sheet 23), the LLM error
analysis (sheet 22), the calibration tables and the matcher ablation.

`insert_into_workbook.py` writes a column of pair-level results (for example a new LLM run or a rerun of
TF-IDF) into sheet 04 of a copy of the workbook; see its help (`python experiments/insert_into_workbook.py -h`).

## Values from the original study

| Values | Workbook | Why |
|---|---|---|
| Labels, rules, matched terms of our approach | sheet 02, N-T | output of the original prototype (Stanford CoreNLP 4.5.5, WordNet 3.1, Word2Vec, DBpedia Spotlight 1.1, local DBpedia and Wikidata); `framework/` implements the same pipeline with other local resources |
| Matcher scores of the 172 term pairs | sheet 10 | same prototype |
| Dandelion scores and ranks | sheets 03, 04 (E) | Dandelion API, discontinued in 2023; the scores are released so the Dandelion results can be recomputed (`02_tfidf/outputs/dandelion_scores_original_study.csv`) |
| Annotations | sheets 02, 15 | three human annotators |
| Study 3 statistics | sheet 14 | recomputed by formulas from the reported means, SDs and group sizes |

## 01_sbert

`sentence-transformers/all-mpnet-base-v2`, normalised embeddings, cosine similarity; related if >= 0.75 (0.60 for
the tuned rows). Three inputs: raw text; `WHAT HOW` concatenation; mean of the WHAT-WHAT and HOW-HOW cosines.

- `sbert_pairs_input.csv`: the input used. For 11 pairs it contains an earlier version of the IDEA003 and IDEA020
  patterns (flagged in sheet 04, column P); `python experiments/build_inputs.py --sheet01` writes
  `sbert_pairs_input_sheet01.csv` with the patterns of sheet 01, and `run_sbert.py --input sbert_pairs_input_sheet01.csv` uses it.
- `outputs/sbert_scores.csv`: the reported scores (sheet 04).
- `python experiments/01_sbert/run_sbert.py` (needs `pip install sentence-transformers`): recomputes them and
  compares with the workbook. Other torch or sentence-transformers versions can change the last decimals.

## 02_tfidf

scikit-learn `TfidfVectorizer` (lowercase, English stop words, sublinear tf), fitted on the 52 idea texts; cosine
of the raw idea texts. `python experiments/02_tfidf/run_tfidf.py` recomputes the cosines, the 5-fold
cross-validated threshold (seed 2026; F1 0.423), the threshold 0.20 tuned on the test labels (F1 0.528) and the
sweep of Table 12, and checks them against sheet 04.

## 03_llm_pair_classification

See `03_llm_pair_classification/README.md` for the models, dates and how the runs were made.

- `prompts/`: `raw_text_per_pair.txt` (raw-text runs of GPT-4o, Claude Sonnet 5.5 and Gemini 2.5 Flash),
  `what_how_chatgpt_app_file.txt` (GPT-4o WHAT+HOW runs), `what_how_definitions_file.txt` (GPT-4o WHAT+HOW runs
  with the definitions of the five types). The same prompts are in sheet 17.
- `inputs/`: `raw_text_240.csv`, `what_how_240_as_run.csv`, `what_how_240_definitions.csv` (patterns of sheet 01).
- `outputs/`: one file per reported run (`runs.csv` lists model, condition and date);
  `outputs/raw_chat_answers/` holds the tables returned by the chat for the definitions runs.
- `score_llm.py`: binary and five-way metrics and Cohen's kappa between runs; with no argument it scores the eight
  reported runs and checks them against sheet 04. Any `Pair_ID, label` file can be scored.
- `run_llm_api.py`: the same question through the OpenAI, Anthropic or Google API, one call per pair (an
  alternative to the chat runs; its labels are not the reported ones).

## 04_triple_extraction

The 70 WHAT/HOW phrases of the 35 Study 4 ideas, Stanford OpenIE vs GPT-4o.

- `patterns_70.csv`: input. `prompt_chatgpt_app.txt`: the prompt used in the ChatGPT app (GPT-4o, October 2026).
- `outputs/openie_vs_gpt4o_judged.csv`: OpenIE and GPT-4o triples, the expert flags, the expected triples and the
  Correct / Not Correct judgements (lenient and strict).
- `score_extraction.py`: precision and recall per pattern and extractor (WHAT OpenIE recall 0.750; HOW recall
  0.310 for OpenIE and 0.517 for GPT-4o with lenient judging). Its docstring explains how to judge a new extractor.

## 05_adelie_optional

ADELIE (Qi et al., 2024) on the 52 full idea texts, run by the authors: 57 triples for 50 ideas.
`outputs/adelie_raw_model_output.csv` holds the raw model output, `outputs/adelie_triples.csv` the cleaned triples
(sheet 24). `score_adelie.py` computes the pair scores (best word overlap of two triples), the 5-fold CV threshold
and F1 (0.250 on 222 scored pairs, against 0.636 for our approach on the same pairs). To extract triples with
ADELIE on new text, the framework has an `adelie` extractor (`framework/v1`, `--extractor adelie`).

## 06_sampling_strata

`sampling_pattern.py` reads the 4,465 population pairs and their Dandelion ranks (sheet 03) and prints the pairs
per rank band (141 / 60 / 0 / 39), where the partners sit in their seed idea's ranking (126 in the top five, 200
among the 30 most similar, 39 among the 15 least similar, 1 in the middle) and the 22 seed ideas with partners
from both ends.

## 07_candidate_screening

`screening.py` recomputes the shared content words of all 1,326 pairs of the 52 test ideas (446 pairs kept, 66%
of the comparisons avoided, 27 of the 28 related test pairs kept) and checks them against sheet 20. Needs NLTK's
WordNet (`python -c "import nltk; nltk.download('wordnet')"`).

## 08_runtime

See `08_runtime/README.md`.
