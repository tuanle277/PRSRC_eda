"""Lightweight EDA entry script.

All reusable helpers live in `utils.py`. This file is intentionally kept small
so you can experiment here and call into the shared utilities as needed.
"""

from utils import (
    count_duplicate_encounter_ids,
    count_negative_age_years_rows,
    extract_yellow_highlights_to_file,
    profile_nulls_and_mixed_types,
)

import pandas as pd

def main() -> None:
    """Example EDA entry point. Adjust or replace as needed."""
    # Example: duplicate EncounterId checks in the main PRSRC folder
    # count_duplicate_encounter_ids("PRSRC Data Lock 2.20.26-selected")
    # extract_yellow_highlights_to_file("Data Elements for Broad Sharing TM.DL (2).docx")

    df = pd.read_csv("Data Elements for Broad Sharing TM.DL (2)_dbtable_yellow.csv")

    unique_first_col = df.iloc[:, 0].nunique()
    print(f"Number of unique entries in the first column: {unique_first_col}")

if __name__ == "__main__":
    main()
