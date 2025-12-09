# reports_viewer.py

import os
import json
import tempfile
from io import BytesIO
from datetime import datetime

import pandas as pd
import streamlit as st
from sqlalchemy import text

from src.utils.logger import get_logger
from src.utils.data_paths import get_file_path
from src.database.db_utils import (
    fetch_user_bills,
    get_distinct_sc_codes,
    get_engine,          # NEW: to query tariff_logic_versions
)
from src.agents.reporting_generating_agent.report_generator import BillAuditReporter

logger = get_logger("AuditReportViewer")


# ---------------------------------------------------------
# Excel helper
# ---------------------------------------------------------
def _df_to_excel_bytes(df: pd.DataFrame, account_id: str | None) -> BytesIO:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Audit Results")
    output.seek(0)
    return output


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

    dates = pd.to_datetime(df["read_date"], errors="coerce")
    dates = dates.dropna()
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
    Build a temporary JSON file containing the tariff logic for the given
    account + service classification, by querying tariff_logic_versions.

    Selection criteria:
      - sc_code = selected SC
      - effective_date <= max_read_date
      - end_date IS NULL OR end_date >= min_read_date

    The resulting list of logic objects is written to a temp .json file,
    whose path is returned and passed into BillAuditReporter.
    """
    sc_code = sc_code.strip().upper()

    min_date, max_date = _get_account_read_date_range(account_id)

    engine = get_engine()
    with engine.begin() as conn:
        if min_date is not None and max_date is not None:
            logger.info(
                f"Querying tariff_logic_versions for SC={sc_code} overlapping "
                f"account read_date range {min_date.date()}–{max_date.date()}"
            )
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
                {
                    "sc": sc_code,
                    "min_date": min_date.date(),
                    "max_date": max_date.date(),
                },
            ).mappings().all()
        else:
            # Fallback: use all versions for that SC
            logger.warning(
                "No valid read_date range detected; pulling ALL versions for this SC."
            )
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
        # logic_json might be stored as JSON or text; normalize to dict
        if isinstance(raw_logic, str):
            try:
                logic_obj = json.loads(raw_logic)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse logic_json for SC={sc_code}: {e}")
                continue
        else:
            logic_obj = raw_logic

        # Ensure metadata contains DB effective_date / end_date / sc_code
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

    # Write combined definitions to a temp JSON file
    fd, tmp_path = tempfile.mkstemp(
        prefix=f"tariff_{sc_code}_{account_id}_", suffix=".json"
    )
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(definitions, f, indent=2)

    logger.info(
        f"Wrote {len(definitions)} tariff logic records for SC={sc_code} "
        f"into temp file: {tmp_path}"
    )
    return tmp_path


# ---------------------------------------------------------
# MAIN STREAMLIT VIEW
# ---------------------------------------------------------
def render_report_viewer():
    """
    Streamlit page: Audit Report Viewer

    - User selects account number
    - User selects SC code from dropdown (from DB)
    - We pull matching logic_json rows from tariff_logic_versions based on
      sc_code and the account's bill read_date range.
    - We combine them into a temp JSON file and hand that to BillAuditReporter.
    - We show the text report + tabular results and allow Excel download.
    """

    st.title("🧾 Audit Report Viewer")

    # 1️⃣ Account selection
    accounts = _get_available_accounts()
    if not accounts:
        st.warning("No account numbers found in user_bills.")
        return

    selected_account = st.selectbox(
        "Select Account Number",
        options=accounts,
        index=0,
        help="Choose an account to generate and view its audit report.",
    )

    # 2️⃣ SC selection from DB
    sc_codes = get_distinct_sc_codes()
    if not sc_codes:
        st.error("No Service Classification (SC) codes available in the database.")
        return

    selected_sc = st.selectbox(
        "Service Classification (SC):",
        options=sc_codes,
        help="SC codes are loaded from tariff_logic_versions in the DB.",
    )

    run_audit = st.button("Run Audit for Selected Account")

    if not run_audit:
        st.info("Select an account and SC, then click **Run Audit for Selected Account**.")
        return

    # 3️⃣ Build tariff JSON from DB (sc_code + effective_date range)
    try:
        tariff_json_path = _build_tariff_json_from_db_for_account(
            selected_account, selected_sc
        )
    except Exception as e:
        st.error(f"Failed to build tariff definitions from DB: {e}")
        logger.exception("Error building tariff JSON from DB")
        return

    st.caption(
        f"Using tariff logic from database for SC **{selected_sc}**, "
        f"filtered by this account's bill read dates."
    )

    # 4️⃣ Run audit via BillAuditReporter
    reporter = BillAuditReporter(tariff_json_path, default_sc=selected_sc)


    with st.spinner(
        f"Running audit for account {selected_account} under {selected_sc}..."
    ):
        text_report = reporter.generate_audit(account_id=selected_account)

    if text_report.startswith("Error"):
        st.error(text_report)
        return
    if "No bill data found" in text_report:
        st.warning(text_report)
        return

    results = reporter.last_results or []
    if not results:
        st.info("Audit completed, but no results were produced.")
        return

    results_df = pd.DataFrame(results)

    # 5️⃣ Show report + table
    st.subheader("📄 Audit Text Report")
    st.text_area(
        "Report",
        value=text_report,
        height=300,
        label_visibility="collapsed",
    )

    st.subheader("🔍 Audit Results Table")
    preview_df = results_df.copy()
    if "trace" in preview_df.columns:
        preview_df = preview_df.drop(columns=["trace"])
    st.dataframe(preview_df, width="stretch")

    # 6️⃣ Download as Excel
    excel_bytes = _df_to_excel_bytes(results_df, selected_account)
    st.download_button(
        label="⬇️ Download Audit Report (Excel)",
        data=excel_bytes,
        file_name=f"final_audit_report_{selected_account}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


if __name__ == "__main__":
    render_report_viewer()
