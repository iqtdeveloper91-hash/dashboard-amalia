import pandas as pd
from pathlib import Path

for fname in ["DASHBOARD_II_BIMESTRE.xlsx", "DASHBOARD_III_BIMESTRE.xlsx"]:
    path = Path(fname)
    if not path.exists():
        print(f"Missing file: {path}")
        continue
    xl = pd.ExcelFile(path)
    print(f"\n=== {path.name} sheets: {xl.sheet_names}")
    for sheet in xl.sheet_names:
        df = xl.parse(sheet)
        print(f"\n-- {sheet} --")
        print(df.head())
        print("columns", df.columns.tolist())

        df_raw = xl.parse(sheet, header=None)
        print("raw head:")
        print(df_raw.head())
