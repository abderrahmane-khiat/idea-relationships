# Zero-shot LLM pair classification (Baselines 3 and 4)

Each LLM labels the 240 test pairs as `duplicate`, `generalises`, `alternative-solution`, `similar` or `disjoint`.
Task 1 counts every label except `disjoint` as related; Task 2 scores the labels (macro over the four classes with
human labels).

## Reported runs (sheet 04, prompts in sheet 17)

| Output file | Model, date | Input | Prompt |
|---|---|---|---|
| `GPT4o_raw_R1.csv`, `GPT4o_raw_R2.csv` | GPT-4o, ChatGPT app, Oct 2026, two independent runs | `inputs/raw_text_240.csv` | `prompts/raw_text_per_pair.txt` |
| `Claude_Sonnet55.csv` | Claude Sonnet 5.5, Oct 2026, one run | `inputs/raw_text_240.csv` | `prompts/raw_text_per_pair.txt` |
| `Gemini25Flash.csv` | Gemini 2.5 Flash, Oct 2026, one run | `inputs/raw_text_240.csv` | `prompts/raw_text_per_pair.txt` |
| `GPT4o_WHATHOW_R1.csv`, `GPT4o_WHATHOW_R2.csv` | GPT-4o, ChatGPT app, Oct 2026, two fresh chats | `inputs/what_how_240_as_run.csv` | `prompts/what_how_chatgpt_app_file.txt` |
| `GPT4o_WHATHOW_def_R1.csv`, `GPT4o_WHATHOW_def_R2.csv` | GPT-4o, ChatGPT app, 8 Nov 2026, two fresh chats | `inputs/what_how_240_definitions.csv` | `prompts/what_how_definitions_file.txt` |

The GPT-4o runs used the ChatGPT app with its default settings (the temperature cannot be set there). Only the
label is used; any score an LLM returned is ignored.

For 11 pairs, the WHAT+HOW input of the October runs contains an earlier version of the IDEA003 and IDEA020
patterns (column `input_differs_from_sheet01`; sheet 04, column P). The definitions run uses the patterns of
sheet 01.

## Reproduce the reported numbers

```bash
python experiments/03_llm_pair_classification/score_llm.py
```

prints, for each run, TP/FP/FN/TN, precision, recall, F1 and the macro scores, and Cohen's kappa between R1 and R2
(raw text 0.79, WHAT+HOW 0.49, with definitions 0.575), then checks every output file against sheet 04.

## Make a new run

**In a chat app (as for the reported runs).** Open a new chat, choose the model, attach the input file and paste
the prompt. For `what_how_chatgpt_app_file.txt` the model answers in blocks of 40 pairs; write `next` after each
block. Copy the answers into a file with the columns `Pair_ID,label` (a pasted two-column table saved as `.tsv`
also works) and score it:

```bash
python experiments/03_llm_pair_classification/score_llm.py my_run_R1.csv my_run_R2.csv
```

For a second run, open another new chat and do not mention the first one.

**Through an API.** `run_llm_api.py` asks the same question for each pair, one call per pair (OpenAI, Anthropic
or Google; `pip install openai`, `anthropic` or `google-genai`). Its output goes to
`outputs/api_<model>_<condition>_<run>.csv`. API answers can differ from the app runs, so they are not the
reported values.

```bash
python experiments/03_llm_pair_classification/run_llm_api.py --provider openai --model gpt-4o --condition raw_text --run R1
python experiments/03_llm_pair_classification/run_llm_api.py --provider openai --model gpt-4o --condition raw_text --dry-run   # show the prompt only
```

To add a new run to a copy of the workbook: `python experiments/insert_into_workbook.py <file> --value label --column <new column name>`.
