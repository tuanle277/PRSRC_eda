# NEJM Cohort Replication Plan for PRSRC Data

## 1. Post-surgical visit time window (from NEJM notebooks)

**Valid window:** `DaysPostOp >= 274` and `DaysPostOp <= 729`

- **274 days** ≈ 9 months
- **729 days** ≈ 24 months (2 years)
- **Interpretation:** Include follow-up visits between **9 and 24 months** after Chiari surgery

**Implementation steps:**
1. Get `ChiariSurgeryDate` from Treatment table (or ChiariDecompression date)
2. For each follow-up visit, compute `DaysPostOp = VisitDate - ChiariSurgeryDate`
3. Filter to visits where `274 <= DaysPostOp <= 729`
4. For patients with multiple visits in window: use **latest** visit per subject (as in NEJM)

**Note:** The exact window may be adjusted later; this matches the current NEJM cohort definition.

---

## 2. Supplementary Table 3 and Table 6 variables

**Status:** Supplementary Table 3 and Table 6 were referenced as "attached" but are not in the project. To proceed:

- Please share the tables (e.g. as CSV, Excel, or image) so we can:
  1. Extract the exact variable names
  2. Map them to PRSRC database columns
  3. Compute distributions and missingness

Once the variable lists are available, we can:
- Extract them from `data/removed_sites/age_years/column_subset/merged_by_EncounterId.csv` (or individual tables)
- Generate distribution summaries and missingness reports
- Use `extract_supplementary_variables.py` (to be created once tables are shared)

---

## 3. NEJM processing and grouping (for Thanda / Dr. Limbrick review)

From `NEJM_table_code/` notebooks:

### Time filtering
- `filtered_followup = followup[(DaysPostOp >= 274) & (DaysPostOp <= 729)]`
- Per subject: take **latest** visit in window (sorted by FollowupDate)

### Symptom variables (Table 2)
- **Preop source:** SymptomHistory
- **Postop source:** FollowupSymptoms (ExamDate/FollowupDate)
- **Encoding:** 0/1/3/5 (e.g. 0=absent, 1=present, 3=stable, 5=unknown); `PreviouslyReportedHeadaches` uses 0→5 replacement for "not reported"
- **Outcome categories:** Resolved, Improved, Stable, Worse, Unknown, Not Applicable

### Neurological exam variables (Table 2)
- **Preop source:** NeurologicalExamination
- **Postop source:** FollowupNeuroExam (ExamDate)
- **Presence encoding:** e.g. Papilledema==0 → present, Nystagmus==1 → present, strength==0 → weak
- **Refined/Limonadi:** Multiple encoding schemes (Index, Refined, Limonadi) for different analyses

### Preop → postop mappings (examples)
**Symptoms:** Headache→PreviouslyReportedHeadaches, DoubleVision→IndexDoubleVisionSymptoms, etc.
**Neuro:** Papilledema→Papilledema, Nystagmus→Nystagmus, strength columns→corresponding FU columns

### Grouping
- **PFD vs PFDD:** From Site Allocation (PFD, PFDExtension, Allocation)
- **Combo groups:** e.g. combined upper/lower extremity weakness, DLT groups

**Action:** Thanda to confirm with Dr. Limbrick the exact grouping rules and encoding (0/1/3/5, Refined vs Limonadi, etc.) before applying to PRSRC data.

### NEJM variable mappings (for reference)

**Symptoms (preop → refined postop):**  
Preop_Headache→Refined_PreviouslyReportedHeadaches, Preop_DoubleVision→Refined/IndexDoubleVisionSymptoms, Preop_SensorySymptoms→IndexSensoryDeficitSymptoms, Preop_WeaknessSymptoms→IndexWeaknessSymptoms, Preop_Dysphagia→IndexDysphagiaSymptoms, Preop_Hoarseness→IndexHoarsenessSymptoms, Preop_Choking→IndexChokingSymptoms, Preop_SleepApnea→IndexSleepApneaSymptoms, Preop_ShortnessOfBreath→IndexSOBSymptoms, Preop_NeckPain→IndexNeckPainSymptoms, Preop_BackPain→IndexBackPainSymptoms, Preop_TrunkPain→IndexTrunkPainSymptoms, Preop_UpperExtremityPain→IndexUpperExtremPainSymptoms, Preop_LowerExtremityPain→IndexLowerExtremPainSymptoms, Preop_Tremors→IndexTremorsSymptoms, Preop_BalanceOrGaitAtaxia→IndexGaitAtaxiaSymptoms, Preop_Incontinence→IndexIncontinenceSymptoms, Preop_SexualDysfunction→IndexSexualDysfunctionSymptoms

**Neurological (preop → refined postop):**  
Preop_Papilledema→Refined_Papilledema, Preop_Nystagmus→Refined_Nystagmus, Preop_DisconjugateGaze→Refined_DisconjugateGaze, Preop_ExtraocularPalsies→Refined_ExtraocularPalsies, etc. (see step3 notebooks for full list)

---

## 4. Data sources in PRSRC

| NEJM source              | PRSRC equivalent (in age_years)      |
|--------------------------|--------------------------------------|
| Locked.PFD.SymptomHistory| SymptomHistory(1).csv                |
| FollowupSymptoms         | FollowupSymptoms(1).csv             |
| NeurologicalExamination | NeurologicalExamination(1).csv      |
| FollowupNeuroExam        | FollowupNeuroExam.csv               |
| Treatment (ChiariSurgeryDate) | Treatment(1).csv, Treatment2(1).csv |
| Site Allocation          | May need separate file or Site column |

**Date columns:** In age_years, dates are stored as **age in years** (de-identified). To compute DaysPostOp we need either:
- Raw date columns from a non-deidentified version, or
- Age-at-visit and age-at-surgery to infer relative timing (e.g. visit age - surgery age in years × 365)

---

## 5. Next steps

1. **Filter post-surgical visits:** Implement 274–729 day window on PRSRC data (see `filter_postop_visits.py`)
2. **Supplementary Tables:** Share Table 3 and Table 6 variable lists → extract and profile
3. **NEJM encoding:** Confirm grouping/encoding with Dr. Limbrick → apply to PRSRC
