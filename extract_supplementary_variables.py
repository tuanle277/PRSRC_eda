"""
Extract outcome variables from Supplementary Table 3 and Supplementary Table 6.

PLACEHOLDER: Variable lists need to be filled in once the tables are shared.
This script will:
  1. Load filtered post-op visits (from filter_postop_visits.py)
  2. Extract the specified variables
  3. Report distributions and missingness

Run: python extract_supplementary_variables.py
"""

from pathlib import Path

import pandas as pd

# --- FILL IN ONCE TABLES ARE AVAILABLE ---
# Supplementary Table 3 variables (outcome variables for predictive modeling)
SUPP_TABLE_3_VARS: list[str] = [
    # Example placeholders from NEJM Table 2 - replace with actual Table 3 variables:
    # "PreviouslyReportedHeadaches",
    # "IndexDoubleVisionSymptoms",
    # ...
]

# Supplementary Table 6 variables
SUPP_TABLE_6_VARS: list[str] = [
    # Example placeholders - replace with actual Table 6 variables:
    # ...
]

DATA_DIR = Path(__file__).resolve().parent / "data" / "removed_sites"
OUTPUT_DIR = Path(__file__).resolve().parent / "output"
FILTERED_SYMPTOMS = OUTPUT_DIR / "filtered_postop_visits_symptoms.csv"
FILTERED_NEURO = OUTPUT_DIR / "filtered_postop_visits_neuro.csv"
MERGED_PATH = Path(__file__).resolve().parent / "data" / "removed_sites" / "age_years" / "column_subset" / "merged_by_EncounterId.csv"


def summarize_distributions(df: pd.DataFrame, vars_list: list[str], label: str) -> pd.DataFrame:
    """Compute distribution and missingness for each variable."""
    results = []
    for col in vars_list:
        if col not in df.columns:
            results.append({
                "variable": col,
                "missing": len(df),
                "missing_pct": 100.0,
                "n": 0,
                "distribution": "NOT FOUND",
            })
            continue
        s = df[col]
        n_miss = s.isna().sum()
        n = len(s) - n_miss
        dist = s.value_counts(dropna=False).head(10).to_dict()
        dist_str = "; ".join(f"{k}: {v}" for k, v in list(dist.items())[:5])
        results.append({
            "variable": col,
            "missing": int(n_miss),
            "missing_pct": round(100 * n_miss / len(df), 1),
            "n": int(n),
            "distribution": dist_str,
        })
    return pd.DataFrame(results)


def main():
    all_vars = list(set(SUPP_TABLE_3_VARS + SUPP_TABLE_6_VARS))
    if not all_vars:
        print("No variables defined. Please add variable names from Supplementary Table 3 and 6.")
        return

    # Load filtered visits or merged data
    if FILTERED_SYMPTOMS.exists():
        df_symptoms = pd.read_csv(FILTERED_SYMPTOMS)
        print(f"Loaded {len(df_symptoms)} filtered symptom visits")
    else:
        print("Run filter_postop_visits.py first to create filtered_postop_visits_symptoms.csv")
        df_symptoms = pd.DataFrame()

    if FILTERED_NEURO.exists():
        df_neuro = pd.read_csv(FILTERED_NEURO)
        print(f"Loaded {len(df_neuro)} filtered neuro visits")
    else:
        df_neuro = pd.DataFrame()

    if MERGED_PATH.exists():
        df_merged = pd.read_csv(MERGED_PATH, nrows=1000)  # Sample for column check
        print(f"Merged table has {len(df_merged.columns)} columns")
    else:
        df_merged = pd.DataFrame()

    # Summarize Table 3 vars
    if SUPP_TABLE_3_VARS:
        summary_t3 = summarize_distributions(
            df_symptoms if len(df_symptoms) > 0 else df_merged,
            SUPP_TABLE_3_VARS,
            "Table 3",
        )
        summary_t3.to_csv(OUTPUT_DIR / "supp_table3_distributions.csv", index=False)
        print("\nSupplementary Table 3 summary saved to output/supp_table3_distributions.csv")

    # Summarize Table 6 vars
    if SUPP_TABLE_6_VARS:
        summary_t6 = summarize_distributions(
            df_neuro if len(df_neuro) > 0 else df_merged,
            SUPP_TABLE_6_VARS,
            "Table 6",
        )
        summary_t6.to_csv(OUTPUT_DIR / "supp_table6_distributions.csv", index=False)
        print("Supplementary Table 6 summary saved to output/supp_table6_distributions.csv")


if __name__ == "__main__":
    main()
