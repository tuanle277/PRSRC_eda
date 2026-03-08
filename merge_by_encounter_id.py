"""
Merge all CSVs in a folder that have EncounterId into one table (outer join on EncounterId).
Duplicate column names (other than EncounterId) get suffixed with _Tablename.
"""
import re
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data" / "removed_sites" / "age_years"
OUTPUT_PATH = PROJECT_ROOT / "data" / "removed_sites" / "age_years" / "column_subset" / "merged_by_EncounterId.csv"


def _safe_name(stem: str) -> str:
    """File-name-safe suffix (no spaces, no parens)."""
    return re.sub(r"[^\w]", "_", stem).strip("_") or "t"


def _read_csv(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path, on_bad_lines="skip", engine="python", encoding="utf-8")
    except UnicodeDecodeError:
        return pd.read_csv(path, on_bad_lines="skip", engine="python", encoding="latin-1")


def main():
    data_dir = Path(DATA_DIR)
    if not data_dir.is_dir():
        raise FileNotFoundError(f"Data dir not found: {data_dir}")

    csv_files = sorted(data_dir.glob("*.csv"))
    tables: list[tuple[str, pd.DataFrame]] = []

    for path in csv_files:
        if path.name.startswith("merged_") or path.name == "nulls_mixed_types_report.csv":
            continue
        df = _read_csv(path)
        if "EncounterId" not in df.columns:
            continue
        tables.append((path.stem, df))

    if not tables:
        print("No CSVs with EncounterId found.")
        return

    base_name, merged = tables[0]
    merged = merged.copy()
    print(f"Base: {base_name} ({len(merged):,} rows, {len(merged.columns)} cols)")

    for name, df in tables[1:]:
        suffix = _safe_name(name)
        # Rename columns that already exist (except EncounterId) to avoid overwrite
        existing = set(merged.columns) - {"EncounterId"}
        new_cols = {}
        for c in df.columns:
            if c != "EncounterId" and c in existing:
                new_cols[c] = f"{c}_{suffix}"
        df = df.rename(columns=new_cols)
        before = len(merged)
        merged = merged.merge(df, on="EncounterId", how="outer")
        print(f"  + {name} -> {len(merged):,} rows, {len(merged.columns)} cols")
        if len(merged) > before:
            print(f"    (added {len(merged) - before:,} encounter rows)")

    merged.to_csv(OUTPUT_PATH, index=False)
    print(f"\nWrote {OUTPUT_PATH} ({len(merged):,} rows, {len(merged.columns)} columns)")


if __name__ == "__main__":
    main()
