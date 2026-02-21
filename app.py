"""
Streamlit UI: tables + merge column + SQL. No full CSV load — metadata only + DuckDB read_csv_auto for instant UI.
"""
import os
import re
import streamlit as st
import pandas as pd

try:
    import duckdb
except ImportError:
    duckdb = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DATA_PATH = os.path.join(
    BASE_DIR, "PRSRC Data Lock 2.20.26-selected", "removed_sites", "age_years"
)


def _table_name(filename: str) -> str:
    name = filename.replace(".csv", "")
    return re.sub(r"[^\w]", "_", name).strip("_") or "t"


@st.cache_data(ttl=3600)
def get_tables_and_paths(data_path: str) -> tuple[list[str], dict[str, str]]:
    """Return (sorted table names, table_name -> absolute path). No data read."""
    if not os.path.isdir(data_path):
        return [], {}
    abspath = os.path.abspath(data_path)
    names, paths = [], {}
    for f in sorted(os.listdir(abspath)):
        if not f.lower().endswith(".csv"):
            continue
        path = os.path.join(abspath, f)
        name = _table_name(f)
        names.append(name)
        paths[name] = path.replace("\\", "/")
    return names, paths


@st.cache_data(ttl=3600)
def get_columns(_path: str) -> list[str]:
    """Header-only read for column names (instant)."""
    try:
        return pd.read_csv(_path, nrows=0, encoding="utf-8").columns.tolist()
    except Exception:
        try:
            return pd.read_csv(_path, nrows=0, encoding="latin-1").columns.tolist()
        except Exception:
            return []


# Preferred merge columns (order preserved in dropdown)
PREFERRED_MERGE_COLUMNS = ["Subject", "SubjectId", "EncounterId", "EncounterDate"]


def common_columns(table_paths: dict[str, str], table_names: list[str]) -> list[str]:
    """Columns that appear in every selected table."""
    if not table_names:
        return []
    cols = set(get_columns(table_paths[table_names[0]]))
    for t in table_names[1:]:
        cols &= set(get_columns(table_paths[t]))
    return sorted(cols)


def merge_column_options(table_paths: dict[str, str], table_names: list[str]) -> list[str]:
    """Merge dropdown: preferred columns first (Subject, SubjectId, EncounterId, EncounterDate), then rest."""
    common = common_columns(table_paths, table_names)
    if not common:
        return []
    preferred = [c for c in PREFERRED_MERGE_COLUMNS if c in common]
    rest = sorted(c for c in common if c not in PREFERRED_MERGE_COLUMNS)
    return preferred + rest


def _sql_escape_path(path: str) -> str:
    return path.replace("'", "''")


def _parse_filter_values(text: str, numeric: bool = True) -> list[str] | None:
    """Parse '1, 2, 3' or '1' into list of SQL-safe values. Returns None if empty."""
    if not text or not str(text).strip():
        return None
    parts = [p.strip() for p in str(text).split(",") if p.strip()]
    if not parts:
        return None
    if numeric:
        return [p for p in parts if p.lstrip("-").isdigit()]
    return [f"'{p.replace(chr(39), chr(39)+chr(39))}'" for p in parts]


def _where_from_filters(subject_id: str, encounter_id: str, site: str, first_alias: str = "t0") -> str:
    """Build WHERE clause from search textboxes. first_alias is the table alias (e.g. t0)."""
    conditions = []
    for col, raw, numeric in [
        ("SubjectId", subject_id, True),
        ("EncounterId", encounter_id, True),
        ("Site", site, True),
    ]:
        vals = _parse_filter_values(raw, numeric=numeric)
        if vals:
            conditions.append(f"{first_alias}.{col} IN ({','.join(vals)})")
    if not conditions:
        return ""
    return " WHERE " + " AND ".join(conditions)


def _sql_with_csv_refs(sql: str, table_paths: dict[str, str], selected: list[str]) -> str:
    """Replace table names in SQL with read_csv_auto('path') for direct CSV querying."""
    out = sql
    for name in selected:
        if name not in table_paths:
            continue
        path = _sql_escape_path(table_paths[name])
        ref = f"read_csv_auto('{path}')"
        out = re.sub(rf"\b{re.escape(name)}\b", ref, out)
    return out


@st.cache_data(ttl=3600)
def _preview_table(_path: str, limit: int = 5) -> pd.DataFrame:
    """First N rows from CSV via DuckDB (cached)."""
    con = duckdb.connect(":memory:")
    return con.execute(f"SELECT * FROM read_csv_auto('{_sql_escape_path(_path)}') LIMIT {limit}").fetchdf()


def main():
    st.set_page_config(page_title="PRSRC Query", layout="wide")
    st.title("PRSRC data: tables + SQL")

    data_path = st.sidebar.text_input(
        "Data folder",
        value=DEFAULT_DATA_PATH,
        help="Path to folder containing CSV tables (e.g. removed_sites/age_years)",
    )

    table_names, table_paths = get_tables_and_paths(data_path)
    if not table_names:
        st.error(f"No CSV files found in: {data_path}")
        return
    # Apply "Select all" / "Clear" before multiselect is created (Streamlit forbids changing widget key after creation)
    if st.session_state.get("_pending_tables") == "all":
        st.session_state.tables_multiselect = list(table_names)
        del st.session_state["_pending_tables"]
        st.rerun()
    if st.session_state.get("_pending_tables") == "clear":
        st.session_state.tables_multiselect = []
        del st.session_state["_pending_tables"]
        st.rerun()

    if "include_all_tables" not in st.session_state:
        st.session_state.include_all_tables = False
    st.sidebar.checkbox(
        "Include all tables",
        value=st.session_state.include_all_tables,
        key="include_all_tables",
        help="Use every table in the folder.",
    )
    default_tables = table_names if st.session_state.include_all_tables else table_names[: min(5, len(table_names))]
    selected = st.sidebar.multiselect(
        "Tables to use",
        options=table_names,
        default=default_tables,
        key="tables_multiselect",
        help="Select which tables to load. Check 'Include all tables' to add all.",
    )
    st.sidebar.button(
        "Select all tables",
        on_click=lambda: st.session_state.update(_pending_tables="all"),
    )
    st.sidebar.button(
        "Clear tables",
        on_click=lambda: st.session_state.update(_pending_tables="clear"),
    )

    if st.session_state.include_all_tables:
        selected = table_names
    if not selected:
        st.sidebar.warning("Select at least one table.")
        return

    if duckdb is None:
        st.error("DuckDB is required for SQL queries. Install with: pip install duckdb")
        return

    merge_opts = merge_column_options(table_paths, selected)
    default_merge = "SubjectId" if "SubjectId" in merge_opts else (merge_opts[0] if merge_opts else None)
    merge_col = st.sidebar.selectbox(
        "Merge column",
        options=["(no merge)"] + merge_opts,
        index=1 + merge_opts.index(default_merge) if default_merge and default_merge in merge_opts else 0,
        help="Join tables on this column. Preferred: Subject, SubjectId, EncounterId, EncounterDate.",
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("**Search / filter** (optional, applied to default query)")
    filter_subject_id = st.sidebar.text_input(
        "SubjectId",
        value="",
        placeholder="e.g. 1 or 1, 2, 3",
        help="Filter by SubjectId; comma-separated for multiple.",
    )
    filter_encounter_id = st.sidebar.text_input(
        "EncounterId",
        value="",
        placeholder="e.g. 1 or 1, 2, 3",
        help="Filter by EncounterId.",
    )
    filter_site = st.sidebar.text_input(
        "Site",
        value="",
        placeholder="e.g. 1 or 1, 2",
        help="Filter by Site.",
    )

    # Default SQL uses table names (readable); paths substituted at Run via _sql_with_csv_refs
    where_clause = _where_from_filters(filter_subject_id, filter_encounter_id, filter_site, first_alias="t0")
    if merge_col and merge_col != "(no merge)" and len(selected) > 1:
        from_part = f"{selected[0]} AS t0"
        for i, t in enumerate(selected[1:], 1):
            from_part += f" JOIN {t} AS t{i} ON t0.{merge_col} = t{i}.{merge_col}"
        default_sql = f"SELECT * FROM {from_part}{where_clause} LIMIT 500"
        st.sidebar.success(f"Merge column **{merge_col}** — default query JOINs all selected tables.")
    else:
        from_part = f"{selected[0]} AS t0"
        default_sql = f"SELECT * FROM {from_part}{where_clause} LIMIT 100"

    st.sidebar.markdown("---")
    st.sidebar.markdown("**Tables:**")
    for t in selected:
        st.sidebar.code(t)

    st.markdown("---")
    st.subheader("SQL query")
    sql = st.text_area(
        "Query (DuckDB SQL)",
        value=default_sql,
        height=140,
        help="Use table names from sidebar. With merge column set, default JOINs all selected tables.",
    )

    if st.button("Run query"):
        try:
            # Resolve table names to read_csv_auto(path)
            run_sql = _sql_with_csv_refs(sql, table_paths, selected)
            # Apply current search filters at run time (in case SQL box was stale)
            if where_clause and " WHERE " not in run_sql.upper():
                run_sql = re.sub(r"\s+LIMIT\s+", where_clause + " LIMIT ", run_sql, flags=re.IGNORECASE, count=1)
                if " WHERE " not in run_sql.upper():
                    run_sql = run_sql.rstrip().rstrip(";") + where_clause
            con = duckdb.connect(":memory:")
            # Reduce memory/temp usage for large JOINs (avoids OutOfMemoryException / temp disk full)
            con.execute("SET threads=2")
            con.execute("SET preserve_insertion_order=false")
            rel = con.execute(run_sql)
            result = rel.fetchdf() if rel is not None else pd.DataFrame()
            st.dataframe(result, use_container_width=True)
            st.caption(f"Rows: {len(result):,}")
        except Exception as e:
            err_msg = str(e).lower()
            if "out of memory" in err_msg or "outofmemory" in err_msg or "temp" in err_msg:
                st.error(
                    "Query ran out of memory or temp space. Try: fewer tables, add SubjectId/EncounterId filter, "
                    "or lower the LIMIT. You can also increase DuckDB temp space with: "
                    "`PRAGMA max_temp_directory_size='10GiB'` in your SQL before the query."
                )
            st.exception(e)

    st.markdown("---")
    with st.expander("Preview: selected tables (first 5 rows)"):
        for name in selected[:8]:
            st.write(f"**{name}**")
            try:
                st.dataframe(_preview_table(table_paths[name]), use_container_width=True)
            except Exception as e:
                st.caption(f"Preview failed: {e}")


if __name__ == "__main__":
    main()
