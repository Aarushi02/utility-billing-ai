# reports_viewer.py

import os
import re
import json
import tempfile
from io import BytesIO
from datetime import datetime

import pandas as pd
import streamlit as st
from sqlalchemy import text

from src.utils.logger import get_logger
from src.database.db_utils import (
    fetch_user_bills,
    get_distinct_sc_codes,
    get_engine,  # query tariff_logic_versions
)
from src.agents.reporting_generating_agent.report_generator import BillAuditReporter

logger = get_logger("AuditReportViewer")


# ---------------------------------------------------------
# Excel helper (FIXED: sanitize sheet names)
# ---------------------------------------------------------
def _safe_excel_sheet_name(name: str, fallback: str = "Audit Results") -> str:
    """
    Excel worksheet name constraints:
      - max 31 characters
      - cannot contain: : \\ / ? * [ ]
      - cannot be empty
    """
    if not name:
        return fallback

    name = str(name)

    # Replace invalid characters
    name = re.sub(r"[:\\/?*\[\]]", " ", name)

    # Optional normalization for UI arrows/dashes
    name = name.replace("→", "-").replace("–", "-").replace("—", "-")

    # Collapse whitespace and trim
    name = re.sub(r"\s+", " ", name).strip()

    # Truncate to 31 chars
    name = name[:31].strip()

    return name if name else fallback


def _df_to_excel_bytes(df: pd.DataFrame, sheet_name: str = "Audit Results") -> BytesIO:
    output = BytesIO()
    safe_name = _safe_excel_sheet_name(sheet_name)
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=safe_name)
    output.seek(0)
    return output


def _safe_filename_token(token: str, fallback: str = "WINDOW") -> str:
    """
    Keep filenames safe across OS:
      - replace spaces with _
      - drop characters that can be problematic
    """
    if not token:
        return fallback
    token = str(token)
    token = token.replace(" ", "_").replace("→", "-")
    token = re.sub(r"[^A-Za-z0-9_.-]+", "", token)
    return token if token else fallback


# ---------------------------------------------------------
# Accounts helper
# ---------------------------------------------------------
def _get_available_accounts() -> list[str]:
    try:
        df = fetch_user_bills(account_id=None)
    except Exception as e:
        logger.error(f"Error fetching bills for account list: {e}")
        return []

    if df is None or df.empty or "bill_account" not in df.columns:
        return []

    accounts = (
        df["bill_account"]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
        .tolist()
    )
    accounts = [a for a in accounts if a]
    accounts.sort()
    return accounts


# ---------------------------------------------------------
# Read-date range for an account
# ---------------------------------------------------------
def _get_account_read_date_range(account_id: str) -> tuple[datetime | None, datetime | None]:
    """
    Return (min_read_date, max_read_date) for the given account,
    based on user_bills.read_date.
    """
    try:
        df = fetch_user_bills(account_id=account_id)
    except Exception as e:
        logger.error(f"Error fetching bills for account {account_id}: {e}")
        return (None, None)

    if df is None or df.empty or "read_date" not in df.columns:
        logger.warning(f"No readable dates for account {account_id}")
        return (None, None)

    dates = pd.to_datetime(df["read_date"], errors="coerce").dropna()
    if dates.empty:
        return (None, None)

    min_date = dates.min()
    max_date = dates.max()
    logger.info(f"Account {account_id} read_date range: {min_date} → {max_date}")
    return (min_date, max_date)


# ---------------------------------------------------------
# Build tariff JSON from DB (tariff_logic_versions)
# ---------------------------------------------------------
def _build_tariff_json_from_db_for_account(account_id: str, sc_code: str) -> str:
    """
    Build a temporary JSON file containing tariff logic for account + SC by querying tariff_logic_versions.

    Selection criteria:
      - sc_code = selected SC
      - effective_date <= max_read_date
      - end_date IS NULL OR end_date >= min_read_date

    Writes combined definitions into a temp .json and returns the path.
    """
    sc_code = sc_code.strip().upper()
    min_date, max_date = _get_account_read_date_range(account_id)

    engine = get_engine()
    with engine.begin() as conn:
        if min_date is not None and max_date is not None:
            query = text(
                """
                SELECT effective_date, end_date, logic_json
                FROM tariff_logic_versions
                WHERE sc_code = :sc
                  AND effective_date <= :max_date
                  AND (end_date IS NULL OR end_date >= :min_date)
                ORDER BY effective_date
                """
            )
            rows = conn.execute(
                query,
                {"sc": sc_code, "min_date": min_date.date(), "max_date": max_date.date()},
            ).mappings().all()
        else:
            logger.warning("No valid read_date range detected; pulling ALL versions for this SC.")
            query = text(
                """
                SELECT effective_date, end_date, logic_json
                FROM tariff_logic_versions
                WHERE sc_code = :sc
                ORDER BY effective_date
                """
            )
            rows = conn.execute(query, {"sc": sc_code}).mappings().all()

    if not rows:
        raise RuntimeError(
            f"No tariff_logic_versions rows found in DB for SC={sc_code} "
            f"and the account's read_date range."
        )

    definitions: list[dict] = []
    for r in rows:
        raw_logic = r["logic_json"]

        if isinstance(raw_logic, str):
            try:
                logic_obj = json.loads(raw_logic)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse logic_json for SC={sc_code}: {e}")
                continue
        else:
            logic_obj = raw_logic

        metadata = logic_obj.get("metadata", {}) or {}
        eff = r["effective_date"]
        end = r["end_date"]

        if eff is not None:
            metadata.setdefault("effective_date", eff.isoformat())
        if end is not None:
            metadata.setdefault("end_date", end.isoformat())
        metadata.setdefault("sc_code", sc_code)
        logic_obj["metadata"] = metadata

        definitions.append(logic_obj)

    if not definitions:
        raise RuntimeError(
            f"All DB rows for SC={sc_code} failed to parse logic_json; nothing to use."
        )

    fd, tmp_path = tempfile.mkstemp(prefix=f"tariff_{sc_code}_{account_id}_", suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(definitions, f, indent=2)

    logger.info(f"Wrote {len(definitions)} tariff logic records for SC={sc_code} into temp file: {tmp_path}")
    return tmp_path


# ---------------------------------------------------------
# 12-month window helpers
# ---------------------------------------------------------
def _detect_date_column(df: pd.DataFrame) -> str | None:
    """
    Prefer deterministic columns first; then fall back to anything containing 'date'.
    """
    if df is None or df.empty:
        return None

    preferred = [
        "read_date",
        "bill_date",
        "date",  # common in your current outputs
        "billing_date",
        "period_start",
        "start_date",
        "service_start",
        "invoice_date",
    ]
    for c in preferred:
        if c in df.columns:
            return c

    for c in df.columns:
        if "date" in c.lower():
            return c

    return None


def _add_12_month_windows(df: pd.DataFrame, date_col: str) -> tuple[pd.DataFrame, list[dict]]:
    """
    Adds:
      __bill_dt       parsed datetime
      __bill_month    period[M]
      __window_id     int (1..N)
      __window_label  str
    """
    out = df.copy()
    out["__bill_dt"] = pd.to_datetime(out[date_col], errors="coerce")
    out = out.dropna(subset=["__bill_dt"]).copy()
    if out.empty:
        return out, []

    out["__bill_month"] = out["__bill_dt"].dt.to_period("M")

    min_month = out["__bill_month"].min()
    min_idx = min_month.year * 12 + min_month.month

    month_idx = out["__bill_month"].apply(lambda p: p.year * 12 + p.month)
    out["__window_id"] = ((month_idx - min_idx) // 12).astype(int) + 1

    windows = []
    for wid in sorted(out["__window_id"].unique()):
        w_df = out[out["__window_id"] == wid]
        w_start = w_df["__bill_month"].min().to_timestamp(how="start").date()
        w_end = w_df["__bill_month"].max().to_timestamp(how="end").date()
        label = f"Window {wid}: {w_start} → {w_end}"
        windows.append({"id": wid, "start": w_start, "end": w_end, "label": label})

    out["__window_label"] = out["__window_id"].map({w["id"]: w["label"] for w in windows})
    return out, windows


def _compute_window_summary(df: pd.DataFrame) -> dict:
    """
    Deterministic summary for your schema:
      - Sum Actual      = SUM(actual)      if present
      - Sum Calculated  = SUM(expected)    if present (fallback to calculated if expected missing)
      - Sum Difference  = SUM(variance)    if present, else SUM(actual-expected)
    """
    summary = {"rows": int(len(df))}

    def _sum(col: str) -> float | None:
        if col not in df.columns:
            return None
        s = pd.to_numeric(df[col], errors="coerce").fillna(0).sum()
        return float(s)

    summary["sum_actual"] = _sum("actual") if "actual" in df.columns else None

    if "expected" in df.columns:
        summary["sum_calculated"] = _sum("expected")
    elif "calculated" in df.columns:
        summary["sum_calculated"] = _sum("calculated")
    else:
        summary["sum_calculated"] = None

    if "variance" in df.columns:
        summary["sum_difference"] = _sum("variance")
    elif "actual" in df.columns and "expected" in df.columns:
        a = pd.to_numeric(df["actual"], errors="coerce").fillna(0)
        e = pd.to_numeric(df["expected"], errors="coerce").fillna(0)
        summary["sum_difference"] = float((a - e).sum())
    else:
        summary["sum_difference"] = None

    return summary


# ---------------------------------------------------------
# MAIN STREAMLIT VIEW
# ---------------------------------------------------------
def render_report_viewer():
    """
    Streamlit page: Audit Report Viewer (12-month window viewing)

    - Select account + SC
    - Click Run Audit once
    - Results persist in session_state so window dropdown does not reset the page
    - Audit text report section removed entirely per request
    """
    st.title("Audit Report Viewer")

    if "audit_results_df" not in st.session_state:
        st.session_state.audit_results_df = None
    if "audit_key" not in st.session_state:
        st.session_state.audit_key = None

    accounts = _get_available_accounts()
    if not accounts:
        st.warning("No account numbers found in user_bills.")
        return

    selected_account = st.selectbox(
        "Select Account Number",
        options=accounts,
        index=0,
        help="Choose an account to generate and view its audit report.",
        key="rv_selected_account",
    )

    sc_codes = get_distinct_sc_codes()
    if not sc_codes:
        st.error("No Service Classification (SC) codes available in the database.")
        return

    selected_sc = st.selectbox(
        "Service Classification (SC):",
        options=sc_codes,
        help="SC codes are loaded from tariff_logic_versions in the DB.",
        key="rv_selected_sc",
    )

    current_key = (selected_account, selected_sc)
    if st.session_state.audit_key is not None and st.session_state.audit_key != current_key:
        st.session_state.audit_results_df = None
        st.session_state.audit_key = None

    run_audit = st.button("Run Audit for Selected Account", key="rv_run_audit")

    if run_audit:
        try:
            tariff_json_path = _build_tariff_json_from_db_for_account(selected_account, selected_sc)
        except Exception as e:
            st.error(f"Failed to build tariff definitions from DB: {e}")
            logger.exception("Error building tariff JSON from DB")
            return

        st.caption(
            f"Using tariff logic from database for SC **{selected_sc}**, "
            f"filtered by this account's bill read dates."
        )

        reporter = BillAuditReporter(tariff_json_path, default_sc=selected_sc)

        with st.spinner(f"Running audit for account {selected_account} under {selected_sc}..."):
            text_report = reporter.generate_audit(account_id=selected_account)

        if isinstance(text_report, str) and text_report.startswith("Error"):
            st.error(text_report)
            return
        if isinstance(text_report, str) and "No bill data found" in text_report:
            st.warning(text_report)
            return

        results = reporter.last_results or []
        if not results:
            st.info("Audit completed, but no results were produced.")
            return

        st.session_state.audit_results_df = pd.DataFrame(results)
        st.session_state.audit_key = current_key

    if st.session_state.audit_results_df is None or st.session_state.audit_results_df.empty:
        st.info("Select an account and SC, then click **Run Audit for Selected Account**.")
        return

    results_df = st.session_state.audit_results_df

    base_df = results_df.copy()
    if "trace" in base_df.columns:
        base_df = base_df.drop(columns=["trace"])

    st.subheader("Calculation Report by 12-Month Windows")

    date_col = _detect_date_column(base_df)
    if not date_col:
        st.warning(
            "Could not detect a date column in the audit results (e.g., read_date, bill_date, date). "
            "Add a date field to reporter.last_results to enable 12-month window viewing."
        )
    else:
        windowed_df, windows = _add_12_month_windows(base_df, date_col=date_col)

        if windowed_df.empty or not windows:
            st.warning(f"Detected `{date_col}`, but could not form 12-month windows (no valid dates after parsing).")
        else:
            st.caption(f"Windows derived from `{date_col}` (grouped by month into consecutive 12-month blocks).")

            options = ["All results (no window filter)"] + [w["label"] for w in windows]
            selected_window = st.selectbox(
                "Select a 12-month window:",
                options=options,
                index=0,
                key="rv_selected_window",
            )

            if selected_window == "All results (no window filter)":
                view_df = windowed_df.copy()
                file_suffix = "ALL"
                sheet_name = "All Results"
            else:
                view_df = windowed_df[windowed_df["__window_label"] == selected_window].copy()
                file_suffix = _safe_filename_token(selected_window.split(":")[0].replace(" ", "_").upper(), "WINDOW")
                sheet_name = selected_window  # will be sanitized inside _df_to_excel_bytes

            summary = _compute_window_summary(view_df)

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Rows", f"{summary.get('rows', 0):,}")
            c2.metric("Sum Actual", f"${summary['sum_actual']:,.2f}" if summary.get("sum_actual") is not None else "—")
            c3.metric("Sum Calculated", f"${summary['sum_calculated']:,.2f}" if summary.get("sum_calculated") is not None else "—")
            c4.metric("Sum Difference", f"${summary['sum_difference']:,.2f}" if summary.get("sum_difference") is not None else "—")

            st.subheader("Window Results Table")
            display_df = view_df.drop(
                columns=[c for c in ["__bill_dt", "__bill_month", "__window_id", "__window_label"] if c in view_df.columns],
                errors="ignore",
            )
            st.dataframe(display_df, width="stretch")

            st.download_button(
                label="Download Selected Window (Excel)",
                data=_df_to_excel_bytes(display_df, sheet_name=sheet_name),
                file_name=f"final_audit_report_{selected_account}_{file_suffix}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="rv_download_window",
            )

    st.subheader("Audit Results Table (Overall)")
    st.dataframe(base_df, width="stretch")

    st.subheader("Download Overall Audit (Excel)")
    st.download_button(
        label="Download Audit Report (Excel)",
        data=_df_to_excel_bytes(base_df, sheet_name="Overall Audit"),
        file_name=f"final_audit_report_{selected_account}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="rv_download_overall",
    )


if __name__ == "__main__":
    render_report_viewer()
