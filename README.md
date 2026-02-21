# PRSRC Data Prep

Small pipeline to filter and de-identify PRSRC CSV exports: drop selected sites, then convert date columns to age in years (2 decimals).

## Requirements

- Python 3
- `pandas`, `python-dateutil`

```bash
pip install pandas python-dateutil
```

## Data

Place your CSVs in **`PRSRC Data Lock 2.20.26-selected/`**. The Subject table must be **`Subject(1).csv`** with columns `SubjectId` and `BirthDate`.

## Scripts

### 1. Remove sites — `remove_site_column.py`

- **Input:** All CSVs in `PRSRC Data Lock 2.20.26-selected/`
- **Action:** Keeps only rows where `Site` is **not** in `[5, 6, 16, 17, 19, 29]`. Site column is kept.
- **Output:** `PRSRC Data Lock 2.20.26-selected/removed_sites/`

```bash
python remove_site_column.py
```

### 2. Dates → age (years) — `deidentify_age_years.py`

- **Input:** All CSVs in the same folder (e.g. main folder or `removed_sites/`)
- **Action:** Finds columns whose names look like dates (e.g. contain `"date"`), looks up DOB from `Subject(1).csv` by `SubjectId`, and replaces each date with **age in years** = `(date - BirthDate)` using `relativedelta`, rounded to 2 decimals. BirthDate is unchanged.
- **Output:** `<input_folder>/age_years/`

```bash
python deidentify_age_years.py
```

By default it reads from `PRSRC Data Lock 2.20.26-selected`. To run on `removed_sites` instead, call from Python:

```python
from deidentify_age_years import convert_date_columns_to_age_years, path
convert_date_columns_to_age_years(path + "/removed_sites")
```

### 3. Query UI — `app.py` (Streamlit)

- **Data:** Any folder of CSVs (default: `removed_sites/age_years/`).
- **Features:** Load all tables (cached), choose which tables to use, **choose merge column** (e.g. `SubjectId`, `EncounterId`) common to selected tables, then run **DuckDB SQL** for fast queries. Default query JOINs all selected tables on the chosen column.

```bash
pip install streamlit duckdb
streamlit run app.py
```

## Typical workflow

1. Run `remove_site_column.py` → get `removed_sites/`.
2. (Optional) Run `deidentify_age_years.py` on `removed_sites` → get `removed_sites/age_years/`.
3. (Optional) Run `streamlit run app.py` to query and merge tables interactively.
# PRSRC_eda
