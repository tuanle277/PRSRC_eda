"""
Filter post-surgical visits using the NEJM cohort time window.

Time window (from NEJM notebooks): DaysPostOp >= 274 and <= 729
  - 274 days ≈ 9 months
  - 729 days ≈ 24 months (2 years)
  - Valid visits: 9–24 months post-Chiari surgery

For each subject with a valid visit in window: keeps the LATEST visit (per NEJM logic).
"""

import os
from pathlib import Path

import pandas as pd

# Configurable window (may be adjusted later)
DAYS_POSTOP_MIN = 274
DAYS_POSTOP_MAX = 729

DATA_DIR = Path(__file__).resolve().parent / "data" / "removed_sites"
OUTPUT_DIR = Path(__file__).resolve().parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def _read_csv(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path, on_bad_lines="skip", engine="python", encoding="utf-8")
    except UnicodeDecodeError:
        return pd.read_csv(path, on_bad_lines="skip", engine="python", encoding="latin-1")


def get_surgery_dates(treatment: pd.DataFrame) -> pd.DataFrame:
    """
    Get Chiari surgery date per SubjectId.
    For encounters where ChiariDecompression==1: use EncounterDate (surgery encounter date).
    Otherwise use ChiariSurgeryDate if populated (NEJM-style).
    """
    tx = treatment.copy()
    tx["EncounterDate"] = pd.to_datetime(tx["EncounterDate"], errors="coerce")
    tx["ChiariSurgeryDate_raw"] = pd.to_datetime(tx["ChiariSurgeryDate"], errors="coerce")

    if "ChiariDecompression" in tx.columns:
        cd_valid = tx["ChiariDecompression"].astype(str).str.strip().isin(["1", "1.0", "True", "true"])
        tx_surg = tx[cd_valid].copy()
        tx_surg["SurgeryDate"] = tx_surg["EncounterDate"].fillna(tx_surg["ChiariSurgeryDate_raw"])
    else:
        tx_surg = tx.copy()
        tx_surg["SurgeryDate"] = tx_surg["ChiariSurgeryDate_raw"]

    # Fallback: if no Chiari decompression rows, use ChiariSurgeryDate from any row
    if len(tx_surg) == 0:
        tx_surg = tx[tx["ChiariSurgeryDate_raw"].notna()].copy()
        tx_surg["SurgeryDate"] = tx_surg["ChiariSurgeryDate_raw"]

    tx_surg = tx_surg[tx_surg["SurgeryDate"].notna()]

    # Earliest surgery date per subject
    surg = (
        tx_surg.groupby("SubjectId")["SurgeryDate"]
        .min()
        .reset_index()
        .rename(columns={"SurgeryDate": "ChiariSurgeryDate"})
    )
    return surg


def filter_visits_in_window(
    followup: pd.DataFrame,
    surgery_dates: pd.DataFrame,
    date_col: str = "FollowupDate",
    subject_col: str = "SubjectId",
) -> pd.DataFrame:
    """
    Filter follow-up visits to 274–729 days post-op.
    For each subject, keep the latest visit in window.
    """
    fu = followup.merge(surgery_dates, on=subject_col, how="inner")
    fu[date_col] = pd.to_datetime(fu[date_col], errors="coerce")
    fu = fu.dropna(subset=[date_col, "ChiariSurgeryDate"])

    fu["DaysPostOp"] = (fu[date_col] - fu["ChiariSurgeryDate"]).dt.days
    in_window = fu[(fu["DaysPostOp"] >= DAYS_POSTOP_MIN) & (fu["DaysPostOp"] <= DAYS_POSTOP_MAX)]

    # Latest visit per subject (per NEJM)
    latest = (
        in_window.sort_values([subject_col, date_col])
        .groupby(subject_col, as_index=False)
        .last()
    )
    return latest


def main():
    treatment_path = DATA_DIR / "Treatment(1).csv"
    followup_symptoms_path = DATA_DIR / "FollowupSymptoms(1).csv"
    followup_neuro_path = DATA_DIR / "FollowupNeuroExam.csv"

    if not treatment_path.exists():
        print(f"Treatment not found: {treatment_path}")
        return

    treatment = _read_csv(treatment_path)
    surgery_dates = get_surgery_dates(treatment)
    n_subjects_with_surgery = len(surgery_dates)
    print(f"Subjects with Chiari surgery date: {n_subjects_with_surgery}")

    results = {"surgery_dates": surgery_dates}

    # FollowupSymptoms
    if followup_symptoms_path.exists():
        fu_symptoms = _read_csv(followup_symptoms_path)
        fu_symptoms["FollowupDate"] = fu_symptoms.get("FollowupDate", fu_symptoms.get("EncounterDate"))
        filtered_symptoms = filter_visits_in_window(
            fu_symptoms, surgery_dates, date_col="FollowupDate"
        )
        results["filtered_followup_symptoms"] = filtered_symptoms
        print(f"FollowupSymptoms: {len(filtered_symptoms)} visits in window (latest per subject)")

    # FollowupNeuroExam
    if followup_neuro_path.exists():
        fu_neuro = _read_csv(followup_neuro_path)
        fu_neuro["FollowupDate"] = fu_neuro.get("ExamDate", fu_neuro.get("EncounterDate"))
        filtered_neuro = filter_visits_in_window(
            fu_neuro, surgery_dates, date_col="FollowupDate"
        )
        results["filtered_followup_neuro"] = filtered_neuro
        print(f"FollowupNeuroExam: {len(filtered_neuro)} visits in window (latest per subject)")

    # Save outputs
    surgery_dates.to_csv(OUTPUT_DIR / "surgery_dates_by_subject.csv", index=False)
    if "filtered_followup_symptoms" in results:
        results["filtered_followup_symptoms"].to_csv(
            OUTPUT_DIR / "filtered_postop_visits_symptoms.csv", index=False
        )
    if "filtered_followup_neuro" in results:
        results["filtered_followup_neuro"].to_csv(
            OUTPUT_DIR / "filtered_postop_visits_neuro.csv", index=False
        )

    print(f"\nOutputs written to {OUTPUT_DIR}")
    return results


if __name__ == "__main__":
    main()
