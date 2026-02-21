import warnings

import pandas as pd
import os
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

path = "data/removed_sites"

csv_files = [f for f in os.listdir(path) if f.endswith('.csv')]

sites_to_remove = [5, 6, 16, 17, 19, 29]


def datedif_months_div12(dob, d):
    rd = relativedelta(d, dob)
    months = rd.years * 12 + rd.months
    return months / 12


def _read_csv(filepath):
    try:
        return pd.read_csv(
            filepath, on_bad_lines="skip", engine="python", encoding="utf-8"
        )
    except UnicodeDecodeError:
        return pd.read_csv(
            filepath, on_bad_lines="skip", engine="python", encoding="latin-1"
        )
    except TypeError:
        try:
            return pd.read_csv(
                filepath, error_bad_lines=False, engine="python", encoding="utf-8"
            )
        except UnicodeDecodeError:
            return pd.read_csv(
                filepath, error_bad_lines=False, engine="python", encoding="latin-1"
            )


def _is_date_column(series, col_name):
    """True if column name suggests a date and values parse as datetime."""
    cn = col_name.lower()
    if "date" not in cn or col_name == "BirthDate":
        return False
    # Exclude flags like InitialConsultationDateKnown
    if "known" in cn or cn.endswith("known"):
        return False
    if series.isna().all():
        return False
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        parsed = pd.to_datetime(series, errors="coerce")
    valid = parsed.notna()
    return valid.sum() / max(1, series.notna().sum()) >= 0.5


def _to_date(d):
    """Convert datetime to date for relativedelta."""
    if pd.isna(d):
        return None
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, date):
        return d
    return None


def convert_date_columns_to_age_years(data_path, output_subdir="age_years"):
    """
    For each CSV: find date columns, merge DOB from Subject, replace date values
    with age in years = datedif_months_div12(dob, date). Writes to data_path/output_subdir.
    """
    data_dir = os.path.abspath(data_path)
    output_dir = os.path.join(data_dir, output_subdir)
    os.makedirs(output_dir, exist_ok=True)

    # Load Subject DOB: SubjectId -> BirthDate (date)
    subject_path = os.path.join(data_dir, "Subject(1).csv")
    if not os.path.isfile(subject_path):
        raise FileNotFoundError(f"Subject(1).csv not found in {data_dir}")
    subject = _read_csv(subject_path)
    if "SubjectId" not in subject.columns or "BirthDate" not in subject.columns:
        raise ValueError("Subject(1).csv must have SubjectId and BirthDate")
    subject["BirthDate"] = pd.to_datetime(subject["BirthDate"], errors="coerce")
    subject["_dob"] = subject["BirthDate"].apply(
        lambda x: x.date() if pd.notna(x) and hasattr(x, "date") else None
    )
    dob_map = subject.drop_duplicates("SubjectId").set_index("SubjectId")["_dob"].to_dict()

    csv_files = [f for f in os.listdir(data_dir) if f.endswith(".csv")]
    processed = []

    for filename in csv_files:
        filepath = os.path.join(data_dir, filename)
        df = _read_csv(filepath).copy()

        if "SubjectId" not in df.columns:
            # No DOB to merge; skip converting dates
            df.to_csv(os.path.join(output_dir, filename), index=False)
            processed.append((filename, 0))
            continue

        df["_dob"] = df["SubjectId"].map(dob_map)

        date_columns = []
        for col in df.columns:
            if col in ("_dob", "BirthDate"):
                continue
            if _is_date_column(df[col], col):
                date_columns.append(col)

        for col in date_columns:
            d_parsed = pd.to_datetime(df[col], errors="coerce")
            ages = [
                round(datedif_months_div12(dob, _to_date(d)), 2)
                if dob is not None and pd.notna(d) and _to_date(d) is not None
                else float("nan")
                for dob, d in zip(df["_dob"], d_parsed)
            ]
            df[col] = ages

        df = df.drop(columns=["_dob"])
        outpath = os.path.join(output_dir, filename)
        df.to_csv(outpath, index=False)
        processed.append((filename, len(date_columns)))

    print(f"Output folder: {output_dir}")
    for f, n in processed:
        print(f"  {f}: {n} date column(s) converted to age (years)")
    return output_dir


if __name__ == "__main__":
    convert_date_columns_to_age_years(path)