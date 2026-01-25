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

# Domain logic: AuditEngine (used for per-row TRA/RDM override calculations)
try:
    from src.agents.audit_calculation_agent.calc_engine_updated import AuditEngine
except Exception:
    AuditEngine = None  # Streamlit UI will show an error if calculator is used

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
# Dynamic bill spreadsheet helpers (TRA/RDM overrides)
# ---------------------------------------------------------
def _pick_first_existing(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def _coerce_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(0.0)


def _clean_column_names_local(df: pd.DataFrame) -> pd.DataFrame:
    """Lightweight column normalizer to align DB extracts with engine keys."""
    if df is None or df.empty:
        return df
    out = df.copy()
    out.columns = [
        re.sub(r"[^a-z0-9_]+", "_", str(c).strip().lower()).strip("_") for c in out.columns
    ]
    return out


def _resolve_bill_grid_columns(df: pd.DataFrame) -> dict | None:
    """
    Resolve columns for the dynamic monthly bill spreadsheet.

    Required:
      - bill date (read_date or bill_date)
      - billed kWh
      - billed demand (kW)
      - actual bill amount
      - service class (optional; if missing we inject selected SC)
    """
    if df is None or df.empty:
        return None

    bill_date_col = _pick_first_existing(df, ["read_date", "bill_date", "date", "billing_date"])
    kwh_col = _pick_first_existing(df, ["billed_kwh", "kwh", "usage_kwh", "total_kwh", "energy_kwh"])
    demand_col = _pick_first_existing(df, ["billed_demand", "demand_kw", "demand", "kw_demand"])
    amount_col = _pick_first_existing(
        df, ["bill_amount", "total_bill", "billed_amount", "amount_due", "current_charges"]
    )
    sc_col = _pick_first_existing(df, ["service_class", "sc_code", "rate_class", "service_classification"])

    if not (bill_date_col and kwh_col and demand_col and amount_col):
        return None

    return {
        "bill_date": bill_date_col,
        "billed_kwh": kwh_col,
        "billed_demand": demand_col,
        "bill_amount": amount_col,
        "service_class": sc_col,  # may be None
    }


def _build_bill_override_grid(df: pd.DataFrame, cols: dict, selected_sc: str) -> pd.DataFrame:
    base_cols = [cols["bill_date"], cols["billed_kwh"], cols["billed_demand"], cols["bill_amount"]]
    if cols.get("service_class"):
        base_cols.append(cols["service_class"])

    out = df[base_cols].copy()

    # Normalize/ensure service class
    if not cols.get("service_class"):
        out["service_class"] = selected_sc
    else:
        # Fill missing with selected_sc to avoid engine ambiguity
        out[cols["service_class"]] = out[cols["service_class"]].fillna(selected_sc)

    # Editable override columns (user enters)
    if "override_tra" not in out.columns:
        out["override_tra"] = 0.0
    if "override_rdm" not in out.columns:
        out["override_rdm"] = 0.0

    return out


def _compute_expected_from_overrides(
    engine: "AuditEngine",
    grid_df: pd.DataFrame,
    cols: dict,
) -> pd.DataFrame:
    """
    Run AuditEngine per row using override_tra/override_rdm to compute expected bill.

    Requires AuditEngine.calculate_expected_bill() to support override_tra + override_rdm
    (override mode).
    """
    rows: list[dict] = []

    for _, r in grid_df.iterrows():
        sc_val = (
            r.get(cols.get("service_class"))
            if cols.get("service_class")
            else r.get("service_class")
        )

        ctx = {
            "read_date": r.get(cols["bill_date"]),
            "bill_date": r.get(cols["bill_date"]),
            "billed_kwh": r.get(cols["billed_kwh"]),
            "billed_demand": r.get(cols["billed_demand"]),
            "bill_amount": r.get(cols["bill_amount"]),
            "service_class": sc_val,
            "override_tra": r.get("override_tra"),
            "override_rdm": r.get("override_rdm"),
        }

        out = engine.calculate_expected_bill(pd.Series(ctx))

        expected_val = out.get("expected_bill", out.get("expected_amount", 0.0))
        variance_val = out.get("variance", 0.0)

        rows.append(
            {
                "Bill Date": ctx["bill_date"],
                "Service Class": out.get("sc_code", sc_val),
                "kWh": float(ctx.get("billed_kwh") or 0.0),
                "Demand (kW)": float(ctx.get("billed_demand") or 0.0),
                "Actual Bill": float(ctx.get("bill_amount") or 0.0),
                "TRA": float(ctx.get("override_tra") or 0.0),
                "RDM": float(ctx.get("override_rdm") or 0.0),
                "Expected Bill": float(expected_val or 0.0),
                "Variance": float(variance_val or 0.0),
                "Status": out.get("status", ""),
            }
        )

    calc_df = pd.DataFrame(rows)
    if not calc_df.empty:
        calc_df["Expected Bill"] = _coerce_numeric(calc_df["Expected Bill"]).round(2)
        calc_df["Actual Bill"] = _coerce_numeric(calc_df["Actual Bill"]).round(2)
        calc_df["Variance"] = _coerce_numeric(calc_df["Variance"]).round(2)
    return calc_df


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
    - Dynamic Expected Bill Calculator supports per-row TRA/RDM overrides
    """
    st.title("Audit Report Viewer")

    if "audit_results_df" not in st.session_state:
        st.session_state.audit_results_df = None
    if "audit_key" not in st.session_state:
        st.session_state.audit_key = None
    if "tariff_json_path" not in st.session_state:
        st.session_state.tariff_json_path = None
    if "tariff_key" not in st.session_state:
        st.session_state.tariff_key = None

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
    if st.session_state.tariff_key is not None and st.session_state.tariff_key != current_key:
        st.session_state.tariff_json_path = None
        st.session_state.tariff_key = None

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
        st.session_state.tariff_json_path = tariff_json_path
        st.session_state.tariff_key = current_key

    # ---------------------------------------------------------
    # Dynamic Expected Bill Calculator (TRA/RDM overrides)
    # ---------------------------------------------------------
    st.subheader("Expected Bill Calculator (TRA/RDM Overrides)")

    if AuditEngine is None:
        st.error(
            "AuditEngine import failed. Ensure src.agents.audit_calculation_agent.calc_engine_updated is available."
        )
    else:
        # Build or reuse tariff JSON path for the current account+SC
        if st.session_state.tariff_json_path is None or st.session_state.tariff_key != current_key:
            try:
                st.session_state.tariff_json_path = _build_tariff_json_from_db_for_account(selected_account, selected_sc)
                st.session_state.tariff_key = current_key
            except Exception as e:
                st.error(f"Failed to build tariff definitions from DB for calculator: {e}")
                st.session_state.tariff_json_path = None

        # Pull raw bills for this account (so we can show the existing bill)
        try:
            df_bills = fetch_user_bills(account_id=selected_account)
            df_bills = _clean_column_names_local(df_bills)
        except Exception as e:
            st.error(f"Failed to fetch user bills for calculator: {e}")
            df_bills = pd.DataFrame()

        if df_bills is None or df_bills.empty:
            st.info("No user bills available to build the calculator grid.")
        else:
            # Filter to selected SC when present
            if "service_class" in df_bills.columns:
                sc_norm = str(selected_sc).strip().upper().replace("-", "")
                df_bills["service_class"] = df_bills["service_class"].astype(str)
                df_bills = df_bills[
                    df_bills["service_class"].str.upper().str.replace("-", "", regex=False) == sc_norm
                ].copy()

            resolved = _resolve_bill_grid_columns(df_bills)
            if not resolved:
                st.info(
                    "Calculator grid could not be formed. Required columns not found.\n\n"
                    "Needed: read_date/bill_date, billed_kwh, billed_demand, bill_amount.\n"
                    "Optional: service_class."
                )
            elif st.session_state.tariff_json_path is None:
                st.info("Tariff definitions are not available; calculator is disabled.")
            else:
                # Build per-account+sc editable grid in session state
                grid_key = f"override_grid_{selected_account}_{selected_sc}"
                if grid_key not in st.session_state:
                    st.session_state[grid_key] = _build_bill_override_grid(df_bills, resolved, selected_sc)

                st.caption(
                    "Edit TRA and RDM per row (override_tra/override_rdm). Expected bill is computed via AuditEngine override mode."
                )

                edited = st.data_editor(
                    st.session_state[grid_key],
                    use_container_width=True,
                    num_rows="fixed",
                    key=f"rv_editor_{selected_account}_{selected_sc}",
                    column_config={
                        "override_tra": st.column_config.NumberColumn("TRA", format="%.5f", step=0.00001),
                        "override_rdm": st.column_config.NumberColumn("RDM", format="%.2f", step=0.01),
                    },
                )
                st.session_state[grid_key] = edited

                # Compute via engine
                try:
                    engine = AuditEngine(st.session_state.tariff_json_path)
                    calc_df = _compute_expected_from_overrides(engine, edited, resolved)
                except Exception as e:
                    st.error(f"Failed to compute expected bills: {e}")
                    calc_df = pd.DataFrame()

                if calc_df is not None and not calc_df.empty:
                    st.dataframe(calc_df, use_container_width=True)

                    c1, c2, c3 = st.columns(3)
                    c1.metric("Total Actual", f"${calc_df['Actual Bill'].sum():,.2f}")
                    c2.metric("Total Expected", f"${calc_df['Expected Bill'].sum():,.2f}")
                    c3.metric("Total Variance", f"${calc_df['Variance'].sum():,.2f}")

                    st.download_button(
                        "Download Expected Bill (Overrides) - Excel",
                        data=_df_to_excel_bytes(calc_df, sheet_name=f"{selected_sc}_Overrides"),
                        file_name=f"expected_bill_overrides_{selected_account}_{selected_sc}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"rv_dl_overrides_{selected_account}_{selected_sc}",
                    )

    # If the user hasn't run the audit yet, we can still provide the calculator.
    if st.session_state.audit_results_df is None or st.session_state.audit_results_df.empty:
        st.info("To view audit results and 12-month windows, click **Run Audit for Selected Account** above.")
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
                file_suffix = _safe_filename_token(
                    selected_window.split(":")[0].replace(" ", "_").upper(), "WINDOW"
                )
                sheet_name = selected_window  # will be sanitized inside _df_to_excel_bytes

            summary = _compute_window_summary(view_df)

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Rows", f"{summary.get('rows', 0):,}")
            c2.metric("Sum Actual", f"${summary['sum_actual']:,.2f}" if summary.get("sum_actual") is not None else "—")
            c3.metric(
                "Sum Calculated",
                f"${summary['sum_calculated']:,.2f}" if summary.get("sum_calculated") is not None else "—",
            )
            c4.metric(
                "Sum Difference",
                f"${summary['sum_difference']:,.2f}" if summary.get("sum_difference") is not None else "—",
            )

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
