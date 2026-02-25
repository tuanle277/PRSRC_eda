#!/usr/bin/env python3
import argparse
import os
import csv
from functools import reduce
from typing import Any, Iterable

try:
    import pandas as pd  # type: ignore
except Exception:  # pragma: no cover
    pd = None


def list_csvs(input_dir: str) -> list[str]:
    return sorted(
        [
            os.path.join(input_dir, f)
            for f in os.listdir(input_dir)
            if f.lower().endswith(".csv")
        ]
    )


NULL_LITERALS = {"", "na", "nan", "null", "none", "n/a"}


def _is_null_cell(v: Any) -> bool:
    if v is None:
        return True
    if isinstance(v, float) and v != v:  # NaN
        return True
    if isinstance(v, str) and v.strip().lower() in NULL_LITERALS:
        return True
    return False


def _infer_cell_type(v: str) -> str:
    s = v.strip()
    if _is_null_cell(s):
        return "null"
    try:
        int(s)
        return "int"
    except Exception:
        pass
    try:
        float(s)
        return "float"
    except Exception:
        pass
    return "str"


def _eda_csv_file(
    path: str, *, sample_rows: int = 20000
) -> tuple[list[dict[str, Any]], list[str]]:
    """
    Returns:
      - per-column stats rows
      - header (columns)
    """
    with open(path, "r", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            return [], []
        cols = list(reader.fieldnames)

        null_counts = {c: 0 for c in cols}
        type_sets: dict[str, set[str]] = {c: set() for c in cols}
        row_count = 0

        for row in reader:
            row_count += 1
            if sample_rows and row_count > sample_rows:
                break
            for c in cols:
                v = row.get(c, "")
                t = _infer_cell_type(v)
                if t == "null":
                    null_counts[c] += 1
                else:
                    type_sets[c].add(t)

        out: list[dict[str, Any]] = []
        file_name = os.path.basename(path)
        for c in cols:
            types = sorted(type_sets[c])
            out.append(
                {
                    "file": file_name,
                    "column": c,
                    "rows_profiled": row_count,
                    "null_count_profiled": int(null_counts[c]),
                    "null_pct_profiled": (null_counts[c] / row_count) if row_count else 0.0,
                    "inferred_types": "|".join(types),
                    "mixed_inferred_types": len(types) > 1,
                }
            )
        return out, cols


def run_eda(
    input_dir: str,
    *,
    report_path: str,
    sample_rows_per_file: int = 20000,
) -> None:
    """
    EDA over all CSV files in a folder: nulls + mixed inferred types per column.

    This does NOT require pandas.
    """
    csv_paths = list_csvs(input_dir)
    if not csv_paths:
        raise SystemExit(f"No .csv files found in: {input_dir}")

    rows: list[dict[str, Any]] = []
    for path in csv_paths:
        file_rows, _ = _eda_csv_file(path, sample_rows=sample_rows_per_file)
        rows.extend(file_rows)

    fieldnames = (
        list(rows[0].keys())
        if rows
        else [
            "file",
            "column",
            "rows_profiled",
            "null_count_profiled",
            "null_pct_profiled",
            "inferred_types",
            "mixed_inferred_types",
        ]
    )
    with open(report_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def read_csv(path: str):
    if pd is None:
        raise SystemExit(
            "pandas is not installed. Run with --check-only (EDA), or install pandas to merge."
        )
    # Avoid chunked inference (mixed-type warnings) from large wide CSVs.
    return pd.read_csv(path, low_memory=False)


def profile_nulls_and_mixed_types(*args: Any, **kwargs: Any) -> list[dict]:
    """
    Backwards-compatible name (kept so existing code doesn't break).
    Prefer `run_eda()` for the folder-level report without pandas.
    """
    raise NotImplementedError("Use run_eda() or the pandas-based path.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Merge all CSVs in data/removed_sites/age_years by EncounterDate."
    )
    parser.add_argument(
        "--input-dir",
        default=os.path.join("data", "removed_sites", "age_years"),
        help="Folder containing the age_years CSV files",
    )
    parser.add_argument(
        "--key",
        default="EncounterDate",
        help="Column name to merge on (default: EncounterDate)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output CSV path (default: <input-dir>/merged_by_EncounterDate.csv)",
    )
    parser.add_argument(
        "--report",
        default=None,
        help="Write null/mixed-type report CSV (default: <input-dir>/nulls_mixed_types_report.csv)",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only generate the report; do not merge",
    )
    parser.add_argument(
        "--sample-rows",
        type=int,
        default=20000,
        help="Rows to profile per file for EDA (default: 20000; 0 = all rows)",
    )
    args = parser.parse_args()

    input_dir = args.input_dir
    key = args.key
    output_path = (
        args.output
        if args.output is not None
        else os.path.join(input_dir, f"merged_by_{key}.csv")
    )

    report_path = (
        args.report
        if args.report is not None
        else os.path.join(input_dir, "nulls_mixed_types_report.csv")
    )

    run_eda(input_dir, report_path=report_path, sample_rows_per_file=args.sample_rows)
    print(f"Wrote report: {report_path}")

    if args.check_only:
        return

    csv_paths = list_csvs(input_dir)
    if not csv_paths:
        raise SystemExit(f"No .csv files found in: {input_dir}")

    frames = []
    for path in csv_paths:
        df = read_csv(path)
        if key not in df.columns:
            continue

        base = os.path.splitext(os.path.basename(path))[0]
        rename = {c: f"{base}__{c}" for c in df.columns if c != key}
        frames.append(df.rename(columns=rename))

    if not frames:
        raise SystemExit(
            f"None of the CSVs in {input_dir} contained the merge key column: {key}"
        )

    merged = reduce(lambda left, right: left.merge(right, on=key, how="outer"), frames)
    merged.to_csv(output_path, index=False)
    print(f"Wrote: {output_path}")


if __name__ == "__main__":
    main()

