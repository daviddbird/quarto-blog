"""Load the 2025 Waste Data Interrogator workbooks into Parquet files in data/interim.

Run from the repo root:  python src/waste_operators/load.py
Needs: pip install pyxlsb pandas duckdb
"""
import re
from pathlib import Path

import duckdb
import pandas as pd

RAW = Path("data/raw")
INTERIM = Path("data/interim")

# keyword in the file name -> (output name, keyword in the sheet name)
SOURCES = {
    "received": ("received", "received"),
    "removed": ("removed", "removed"),
}
HEADER_MARKER = "EPR Number"


def snake(name: str) -> str:
    """'Facility Sub Region ' -> 'facility_sub_region'."""
    return re.sub(r"[^a-z0-9]+", "_", str(name).strip().lower()).strip("_")


def find_file(keyword: str) -> Path:
    matches = [p for p in RAW.glob("*.xlsb") if keyword in p.name.lower()]
    if len(matches) != 1:
        raise FileNotFoundError(
            f"Expected exactly one .xlsb in {RAW} containing '{keyword}', found {matches}"
        )
    return matches[0]


def read_sheet(path: Path, sheet_keyword: str) -> pd.DataFrame:
    xl = pd.ExcelFile(path, engine="pyxlsb")
    sheets = [s for s in xl.sheet_names if s.lower().startswith("2025") and sheet_keyword in s.lower()]
    if len(sheets) != 1:
        raise ValueError(f"Sheet names in {path.name}: {xl.sheet_names}")
    raw = xl.parse(sheets[0], header=None)

    # Find the header row (there may be title rows above it)
    is_header = raw.apply(lambda r: r.astype(str).str.strip().eq(HEADER_MARKER).any(), axis=1)
    header_idx = is_header.idxmax()
    if not is_header.loc[header_idx]:
        raise ValueError(f"No row containing '{HEADER_MARKER}' found in {sheets[0]}")

    df = raw.iloc[header_idx + 1:].copy()
    df.columns = [snake(c) for c in raw.iloc[header_idx]]
    df = df.dropna(how="all").reset_index(drop=True)

    # Tonnes as numbers, everything else as text so mixed-type columns don't break Parquet
    tonnes_cols = [c for c in df.columns if c.startswith("tonnes")]
    for c in df.columns:
        if c in tonnes_cols:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        elif c not in ("easting", "northing"):
            df[c] = df[c].astype("string").str.strip()
        else:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def profile(df: pd.DataFrame, tonnes_col: str) -> None:
    print(f"\nrows: {len(df):,}   columns: {len(df.columns)}")
    print(f"distinct EPR numbers: {df['epr_number'].nunique():,}")
    print(f"distinct operator names: {df['operator'].nunique():,}")
    print(f"distinct site names: {df['site_name'].nunique():,}")
    print(f"total {tonnes_col}: {df[tonnes_col].sum():,.0f}")
    print("\nmissing values (top 10 columns):")
    print(df.isna().sum().sort_values(ascending=False).head(10).to_string())
    print("\ntop 10 operators by tonnes:")
    print(df.groupby("operator")[tonnes_col].sum().nlargest(10).round(0).to_string())

    names_per_permit = df.groupby("epr_number")["operator"].nunique()
    print(f"\npermits with more than one operator spelling: {(names_per_permit > 1).sum():,}")
    permits_per_name = df.groupby("operator")["epr_number"].nunique()
    print(f"operator names covering more than one permit: {(permits_per_name > 1).sum():,}")


if __name__ == "__main__":
    INTERIM.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    for keyword, (out_name, sheet_kw) in SOURCES.items():
        path = find_file(keyword)
        print(f"\n=== {path.name} ===")
        df = read_sheet(path, sheet_kw)
        out = INTERIM / f"waste_{out_name}_2025.parquet"
        con.register("df", df)
        con.execute(f"COPY df TO '{out.as_posix()}' (FORMAT PARQUET)")
        con.unregister("df")
        print(f"wrote {out}")
        profile(df, [c for c in df.columns if c.startswith("tonnes")][0])
