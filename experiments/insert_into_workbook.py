"""Insert a column of pair-level results (scores or labels) into sheet 04 of the data workbook.

    python experiments/insert_into_workbook.py experiments/02_tfidf/outputs/tfidf_scores_rerun.csv --value TFIDF_cosine --column TFIDF_cosine --replace
    python experiments/insert_into_workbook.py experiments/03_llm_pair_classification/outputs/api_gpt-4o_raw_text_R1.csv --value label --column GPT4o_API_raw_R1

The CSV must have a Pair_ID column and the value column (--value). The values are written to the column named
--column of sheet 04, matched by Pair_ID: a new column is added at the end of the sheet, or, with --replace, an
existing column is overwritten. The result is saved to a new file (default data/idea_relationships_data_updated.xlsx);
the original workbook is never changed unless you pass it as --out.
The result sheets are formulas on fixed columns of sheet 04: replacing a column updates them when the file is
opened in Excel or LibreOffice (full recalculation on load is switched on). A new column is not used by any
formula; score it with the scripts of its experiment folder. evaluate.py reads the data columns by name.
"""
import argparse
import copy
import sys
from pathlib import Path

import openpyxl
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from common import S_BASE, WB  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv")
    ap.add_argument("--value", required=True, help="column of the CSV that holds the values")
    ap.add_argument("--column", required=True, help="column name in sheet 04")
    ap.add_argument("--replace", action="store_true", help="overwrite the column if it exists")
    ap.add_argument("--workbook", default=str(WB))
    ap.add_argument("--out", default=str(WB.with_name("idea_relationships_data_updated.xlsx")))
    a = ap.parse_args()

    d = pd.read_csv(a.csv)
    if "Pair_ID" not in d or a.value not in d:
        sys.exit(f"{a.csv} needs the columns Pair_ID and {a.value}")
    vals = dict(zip(d.Pair_ID.astype(str).str.strip(), d[a.value]))
    wb = openpyxl.load_workbook(a.workbook)
    ws = wb[S_BASE]
    header = {ws.cell(1, c).value: c for c in range(1, ws.max_column + 1)}
    if a.column in header and not a.replace:
        sys.exit(f"column {a.column} exists in sheet 04; use --replace to overwrite it or choose another name")
    col = header.get(a.column) or ws.max_column + 1
    if a.column not in header:
        ws.cell(1, col, a.column)._style = copy.copy(ws.cell(1, ws.max_column - 1)._style)
    n = missing = 0
    for r in range(2, ws.max_row + 1):
        pid = ws.cell(r, 1).value
        if not pid:
            continue
        if pid in vals:
            v = vals[pid]
            ws.cell(r, col, None if pd.isna(v) else (v.item() if hasattr(v, "item") else v)); n += 1
        else:
            missing += 1
    wb.calculation.fullCalcOnLoad = True
    if Path(a.out).resolve() == Path(a.workbook).resolve():
        print("writing into the original workbook (as requested with --out)")
    wb.save(a.out)
    print(f"sheet 04, column {openpyxl.utils.get_column_letter(col)} ({a.column}): {n} values written, "
          f"{missing} pairs without a value; saved {a.out}")


if __name__ == "__main__":
    main()
