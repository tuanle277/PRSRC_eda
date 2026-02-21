"""
EDA helpers: duplicate EncounterId counts, negative de-identified age-year row counts.
"""
import os
import pandas as pd

DATA_PATH = "data"
AGE_YEARS_PATH = "data/removed_sites/age_years"


def _read_csv(filepath):
    try:
        return pd.read_csv(filepath, on_bad_lines="skip", engine="python", encoding="utf-8")
    except UnicodeDecodeError:
        return pd.read_csv(filepath, on_bad_lines="skip", engine="python", encoding="latin-1")
    except TypeError:
        try:
            return pd.read_csv(filepath, error_bad_lines=False, engine="python", encoding="utf-8")
        except UnicodeDecodeError:
            return pd.read_csv(filepath, error_bad_lines=False, engine="python", encoding="latin-1")


def main():
    data_dir = os.path.join(os.path.dirname(__file__), DATA_PATH)
    csv_files = sorted([f for f in os.listdir(data_dir) if f.endswith(".csv")])
    results = []

    for filename in csv_files:
        filepath = os.path.join(data_dir, filename)
        df = _read_csv(filepath)
        if "EncounterId" not in df.columns:
            continue
        vc = df["EncounterId"].value_counts()
        duplicated_ids = vc[vc > 1]
        n_duplicated_ids = len(duplicated_ids)
        n_duplicate_rows = (vc[vc > 1] - 1).sum()  # extra rows per duplicated id
        results.append((filename, n_duplicated_ids, int(n_duplicate_rows), len(df)))

    print("EncounterId duplicate counts by sheet (in", DATA_PATH + ")")
    print("-" * 70)
    if not results:
        print("No CSVs with EncounterId column found.")
        return
    for filename, n_dup_ids, n_dup_rows, total_rows in results:
        print(f"  {filename}")
        print(f"    EncounterIds that repeat: {n_dup_ids}  |  Extra rows (duplicates): {n_dup_rows}  |  Total rows: {total_rows}")
    print("-" * 70)
    total_dup_ids = sum(r[1] for r in results)
    total_dup_rows = sum(r[2] for r in results)
    print(f"  Total EncounterIds that repeat (across sheets): {total_dup_ids}")
    print(f"  Total duplicate rows (across sheets): {total_dup_rows}")


def _is_age_years_column(col_name):
    """True if column name matches de-identified age-in-years columns (ex-BirthDate, ex-*Known)."""
    cn = col_name.strip().lower()
    if "date" not in cn or col_name == "BirthDate":
        return False
    if "known" in cn or cn.endswith("known"):
        return False
    return True


def count_negative_age_years_rows(data_path=None):
    """
    Count how many rows have at least one negative value in de-identified age (years) columns
    across CSVs in removed_sites/age_years. Also reports total negative cell count.
    """
    base = os.path.dirname(os.path.abspath(__file__))
    path = data_path or os.path.join(base, AGE_YEARS_PATH)
    if not os.path.isdir(path):
        print(f"Folder not found: {path}")
        return []

    csv_files = sorted([f for f in os.listdir(path) if f.endswith(".csv")])
    results = []  # (filename, n_rows_with_any_negative, n_negative_cells, total_rows)

    for filename in csv_files:
        filepath = os.path.join(path, filename)
        df = _read_csv(filepath)
        age_cols = [c for c in df.columns if _is_age_years_column(c)]
        if not age_cols:
            continue

        # Rows with at least one negative age; total negative cells across age columns
        has_neg = pd.DataFrame({c: pd.to_numeric(df[c], errors="coerce") < 0 for c in age_cols}).any(axis=1)
        rows_with_neg = int(has_neg.sum())
        neg_cells = sum((pd.to_numeric(df[c], errors="coerce") < 0).sum() for c in age_cols)

        results.append((filename, rows_with_neg, int(neg_cells), len(df)))

    print("Negative de-identified age (years) rows in", path)
    print("-" * 70)
    if not results:
        print("No CSVs with age-year columns found.")
        return results
    for filename, n_rows, n_cells, total in results:
        row_label = "row" if n_rows == 1 else "rows"
        print(f"  {filename}: {n_rows} {row_label} with ≥1 negative age  |  {n_cells} negative cells  |  {total} total rows")
    print("-" * 70)
    print(f"  Total rows with ≥1 negative age: {sum(r[1] for r in results)}")
    print(f"  Total negative age cells: {sum(r[2] for r in results)}")
    return results


if __name__ == "__main__":
    main()
