# report_viewer.py

import os
from io import BytesIO

import pandas as pd
import streamlit as st

from src.utils.logger import get_logger
from src.utils.data_paths import get_file_path
from src.database.db_utils import fetch_user_bills
from src.agents.reporting_generating_agent.report_generator import BillAuditReporter

logger = get_logger("AuditReportViewer")


def _df_to_excel_bytes(df: pd.DataFrame, account_id: str | None) -> BytesIO:
    """
    Convert a DataFrame to an in-memory Excel file for download.
    """
    output = BytesIO()
    suffix = account_id if account_id else "all_accounts"
    sheet_name = "Audit Results"

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)

    output.seek(0)
    return output


def _get_available_accounts() -> list[str]:
    """
    Fetch all user_bills from DB and return unique bill_account values.
    """
    try:
        df = fetch_user_bills(account_id=None)
    except Exception as e:
        logger.error(f"Error fetching bills for account list: {e}")
        return []

    if df is None or df.empty:
        return []

    if "bill_account" not in df.columns:
        logger.warning("Column 'bill_account' missing in user_bills result.")
        return []

    accounts = (
        df["bill_account"]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
        .tolist()
    )
    accounts = [a for a in accounts if a]  # remove empty strings
    accounts.sort()
    return accounts


def _get_account_read_years(account_id: str) -> list[int]:
    """
    For a given account, fetch its bills and return the distinct years
    present in the read_date column.
    """
    try:
        df = fetch_user_bills(account_id=account_id)
    except Exception as e:
        logger.error(f"Error fetching bills for account {account_id}: {e}")
        return []

    if df is None or df.empty:
        logger.warning(f"No bills found for account {account_id}")
        return []

    if "read_date" not in df.columns:
        logger.warning("Column 'read_date' missing in user_bills result.")
        return []

    dates = pd.to_datetime(df["read_date"], errors="coerce")
    years = (
        dates.dropna()
        .dt.year.astype("Int64")
        .dropna()
        .unique()
        .tolist()
    )
    years = sorted(int(y) for y in years)
    logger.info(f"Account {account_id} has bills in years: {years}")
    return years


def _build_tariff_sources_for_account(account_id: str):
    """
    Decide which tariff JSON(s) to use for a given account based on the years
    present in its read_date values.

    Logic:
    - If all read_dates are in the same year -> use that year's tariff JSON.
    - If multiple years -> build a list of year-specific tariff JSONs.

    NOTE:
    The *per-bill* selection logic (`read_date > effective_date` and
    "effective_date closest to read_date") should be implemented inside
    the tariff engine / BillAuditReporter using the effective_date fields
    in your JSONs / DB table.
    """
    years = _get_account_read_years(account_id)

    # Fallback: if we couldn't determine years, just use the default file.
    if not years:
        logger.warning(
            "Falling back to default tariff_definitions.json "
            "because no valid years were found for the account."
        )
        default_path = get_file_path("processed", "tariff_definitions.json")
        return default_path

    # Single-year: just one JSON for that year
    if len(years) == 1:
        year = years[0]
        # Example naming convention: tariff_definitions_2021.json
        year_file_name = f"tariff_definitions_{year}.json"
        year_tariff_path = get_file_path("processed", year_file_name)
        logger.info(
            f"Using single-year tariff JSON for account {account_id}: {year_tariff_path}"
        )
        return year_tariff_path

    # Multi-year: build list of JSONs, one per year
    tariff_files = []
    for year in years:
        year_file_name = f"tariff_definitions_{year}.json"
        year_tariff_path = get_file_path("processed", year_file_name)
        tariff_files.append(year_tariff_path)

    logger.info(
        f"Account {account_id} spans multiple years {years}. "
        f"Passing tariff JSONs: {tariff_files}"
    )
    return tariff_files


def render_report_viewer():
    """
    Streamlit page: Audit Report Viewer

    - User selects an account number
    - We determine if its bills span one or multiple years
    - We choose the appropriate tariff JSON(s) based on effective dates / years
    - We run BillAuditReporter.generate_audit(account_id=...)
    - Show the text report and tabular results
    - Provide an Excel download button
    """

    st.title("🧾 Audit Report Viewer")

    # ---------------------------------------------------------
    # 1. Account Selection
    # ---------------------------------------------------------
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

    run_audit = st.button("Run Audit for Selected Account")

    if not run_audit:
        st.info("Select an account and click **Run Audit for Selected Account**.")
        return

    # ---------------------------------------------------------
    # 2. Decide which tariff JSON(s) to use for this account
    #    based on the years in its read_date values.
    # ---------------------------------------------------------
    tariff_source = _build_tariff_sources_for_account(selected_account)

    # Helpful UI hint for you / reviewers
    if isinstance(tariff_source, list):
        st.caption(
            f"Detected bills across multiple years. "
            f"Using year-specific tariff definitions: {', '.join(os.path.basename(p) for p in tariff_source)}"
        )
    else:
        st.caption(
            f"Detected bills in a single year. "
            f"Using tariff definitions file: {os.path.basename(tariff_source)}"
        )

    # ---------------------------------------------------------
    # 3. Initialize BillAuditReporter
    #    (supports either a single file path or a list of paths)
    # ---------------------------------------------------------
    reporter = BillAuditReporter(tariff_source)

    # ---------------------------------------------------------
    # 4. Run audit for the chosen account
    # ---------------------------------------------------------
    with st.spinner(f"Running audit for account {selected_account}..."):
        text_report = reporter.generate_audit(account_id=selected_account)

    # If something went wrong, the reporter returns an error string
    if text_report.startswith("Error"):
        st.error(text_report)
        return
    if "No bill data found" in text_report:
        st.warning(text_report)
        return

    # Convert last_results (list of dicts) into DataFrame
    results = reporter.last_results or []
    if not results:
        st.info("Audit completed, but no results were produced.")
        return

    results_df = pd.DataFrame(results)

    # ---------------------------------------------------------
    # 5. Show text report + DataFrame preview
    # ---------------------------------------------------------
    st.subheader("📄 Audit Text Report")
    st.caption("This is the same human-readable report your CLI script prints.")
    st.text_area(
        "Report",
        value=text_report,
        height=300,
        label_visibility="collapsed",
    )

    st.subheader("🔍 Audit Results Table")
    st.caption(
        "Tabular view of per-bill audit results. Scroll horizontally/vertically to inspect."
    )

    # Optional: hide verbose columns like `trace` from the main preview
    preview_df = results_df.copy()
    if "trace" in preview_df.columns:
        preview_df = preview_df.drop(columns=["trace"])

    st.dataframe(preview_df, width='stretch')

    # ---------------------------------------------------------
    # 6. Download as Excel
    # ---------------------------------------------------------
    excel_bytes = _df_to_excel_bytes(results_df, selected_account)

    st.download_button(
        label="⬇️ Download Audit Report (Excel)",
        data=excel_bytes,
        file_name=f"final_audit_report_{selected_account}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        help="Download the full audit report (including trace column) as an Excel file.",
    )
