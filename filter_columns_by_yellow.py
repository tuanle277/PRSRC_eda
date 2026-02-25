"""
Using the dbtable_yellow CSV, find each database table in data/removed_sites/age_years/
and keep only the columns that appear as highlighted_text for that table.
Outputs to a subfolder column_subset/ so originals are unchanged.
"""
import os
import re
from pathlib import Path

import pandas as pd

# Paths (relative to project root)
PROJECT_ROOT = Path(__file__).resolve().parent
DBTABLE_YELLOW_CSV = PROJECT_ROOT / "Data Elements for Broad Sharing TM.DL (2)_dbtable_yellow.csv"
DATA_DIR = PROJECT_ROOT / "data" / "removed_sites" / "age_years"
OUTPUT_SUBDIR = "column_subset"

# Key columns to always keep if present (so data remains joinable)
KEY_COLUMNS = {"Site", "Subject", "SubjectId", "EncounterId", "EncounterDate"}


def normalize_table_name(name: str) -> str:
    """Normalize for matching: remove '(1)', extra spaces."""
    name = (name or "").strip()
    name = re.sub(r"\s*\(\s*1\s*\)\s*", "", name, flags=re.IGNORECASE)
    return re.sub(r"\s+", "", name)


def filename_stem_to_table_name(stem: str) -> str:
    """e.g. 'Subject(1)' -> 'Subject', 'ChildhoodHistory' -> 'ChildhoodHistory'."""
    return normalize_table_name(stem)


def build_table_to_columns(csv_path: Path) -> dict[str, set[str]]:
    """
    Read dbtable_yellow CSV and return map: normalized_table_name -> set of column names.
    Handles 'Treatment and Treatment2' by assigning columns to both 'Treatment' and 'Treatment2'.
    """
    df = pd.read_csv(csv_path)
    # Group by database_table, collect unique highlighted_text
    out: dict[str, set[str]] = {}
    for db_table, text in df[["database_table", "highlighted_text"]].dropna().itertuples(index=False):
        text = (text or "").strip()
        if not text:
            continue
        # Normalize table name(s): "Treatment and Treatment2" -> add to both Treatment and Treatment2
        if " and " in str(db_table):
            keys = [normalize_table_name(k) for k in str(db_table).split(" and ")]
        else:
            keys = [normalize_table_name(str(db_table))]
        for k in keys:
            if k not in out:
                out[k] = set()
            out[k].add(text)
    return out


def main():
    if not DBTABLE_YELLOW_CSV.exists():
        raise FileNotFoundError(f"Expected: {DBTABLE_YELLOW_CSV}")
    if not DATA_DIR.is_dir():
        raise FileNotFoundError(f"Expected data dir: {DATA_DIR}")

    table_to_columns = build_table_to_columns(DBTABLE_YELLOW_CSV)
    out_dir = DATA_DIR / OUTPUT_SUBDIR
    out_dir.mkdir(parents=True, exist_ok=True)

    csv_files = [f for f in DATA_DIR.iterdir() if f.suffix.lower() == ".csv" and f.name != "nulls_mixed_types_report.csv"]
    written = 0
    skipped = 0

    for path in sorted(csv_files):
        stem = path.stem
        table_key = filename_stem_to_table_name(stem)
        columns_to_keep = table_to_columns.get(table_key)
        if not columns_to_keep:
            skipped += 1
            continue

        try:
            df = pd.read_csv(path, on_bad_lines="skip", engine="python", encoding="utf-8")
        except UnicodeDecodeError:
            df = pd.read_csv(path, on_bad_lines="skip", engine="python", encoding="latin-1")

        # Keep key columns + any column in the yellow list that exists
        existing = set(df.columns)
        keep = (KEY_COLUMNS & existing) | (columns_to_keep & existing)
        if not keep:
            skipped += 1
            continue
        # Preserve original column order: key cols first, then yellow cols in file order
        key_order = [c for c in df.columns if c in KEY_COLUMNS]
        rest = [c for c in df.columns if c in columns_to_keep and c not in KEY_COLUMNS]
        final_cols = key_order + rest
        out_df = df[final_cols]
        out_path = out_dir / path.name
        out_df.to_csv(out_path, index=False)
        written += 1
        print(f"  {path.name} -> {out_path.name} ({len(final_cols)} columns)")

    print(f"\nWrote {written} files to {out_dir}")
    if skipped:
        print(f"Skipped {skipped} CSVs (no matching table in yellow CSV).")


if __name__ == "__main__":
    main()
