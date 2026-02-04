import os
import sys
from datetime import datetime
from typing import List, Dict, Optional, Union


import pandas as pd

from src.utils.logger import get_logger
from src.utils.helpers import clean_column_names
from src.database.utils.user_bills_utils import fetch_user_bills

# ---- Domain logic: updated AuditEngine ------------------------------------
try:
    from src.agents.audit_calculation_agent.calc_engine_updated import AuditEngine
except ImportError as e:
    get_logger("AuditReporter").error(f"Missing domain modules: {e}")
    sys.exit(1)

logger = get_logger("AuditReporter")


class BillAuditReporter:
    """
    Wrapper around AuditEngine.

    In the new design, the Streamlit layer (reports_viewer) already selects
    the correct tariff logic rows from the database (by sc_code and the
    account's bill read_date range), combines their logic_json into a single
    temp JSON file, and passes the path to this class.

    So we only need a *single* AuditEngine instance per report, and
    AuditEngine itself will decide which version/effective_date applies
    for each bill based on the JSON definitions it loads.
    """

    def __init__(self, tariff_source: Union[str, List[str]], default_sc: str | None = None):
        self.last_results: List[Dict] = []
        self.default_sc = default_sc
        
        logger.info(f"Initializing BillAuditReporter with tariff JSON: {tariff_source}")
        try:
            self.engine = AuditEngine(tariff_source)
        except Exception as e:
            logger.error(f"Tariff file initialization failed: {tariff_source} ({e})")
            self.engine = None


    # ------------------------------------------------------------------ #
    # Core: audit directly from user_bills in DB
    # ------------------------------------------------------------------ #

    def generate_audit(self, account_id: Optional[str] = None) -> str:
        """
        Pull pre-existing user_bills from DB, run the calculation engine
        (backed by DB-derived logic_json for the selected SC), persist
        discrepancies, and generate a text report.
        """
        if self.engine is None:
            return "Error: Audit Engine not initialized."

        logger.info(
            f"Starting DB-based audit for account: {account_id if account_id else 'ALL ACCOUNTS'}"
        )

        # 1. Fetch bills from DB
        try:
            df_bills = fetch_user_bills(account_id=account_id)
        except Exception as e:
            logger.error(f"Error fetching bills from DB: {e}")
            return f"Error fetching bills from DB: {str(e)}"

        if df_bills.empty:
            if account_id:
                return f"No bill data found in user_bills for account_id={account_id}."
            return "No bill data found in user_bills table."

        # 2. Data cleaning / normalization
        df_bills = clean_column_names(df_bills)

        # ensure service_class exists
        if "service_class" not in df_bills.columns:
            fallback_sc = self.default_sc or "SC1"
            logger.info(
                f"Service Class missing in user_bills. Defaulting to {fallback_sc!r} for all rows."
                )
            df_bills["service_class"] = fallback_sc

        # numeric columns cleanup
        numeric_cols = [
            "billed_kwh",
            "billed_demand",
            "billed_rkva",
            "bill_amount",
            "days_used",
        ]
        for col in numeric_cols:
            if col in df_bills.columns:
                df_bills[col] = (
                    df_bills[col]
                    .astype(str)
                    .str.replace(r"[$,]", "", regex=True)
                )
                df_bills[col] = pd.to_numeric(df_bills[col], errors="coerce").fillna(0)

        # bill_date as datetime
        if "bill_date" in df_bills.columns:
            df_bills["bill_date"] = pd.to_datetime(
                df_bills["bill_date"], errors="coerce"
            )

        # mapping from df columns -> engine context keys
        column_mapping = {
            "billed_kwh": "billed_kwh",
            "billed_demand": "billed_demand",
            "billed_rkva": "billed_rkva",
            "days_used": "days_used",
            "bill_date": "bill_date",
            "bill_amount": "bill_amount",
            "service_class": "service_class",
            "delivery_voltage": "delivery_voltage",
            "delivery_voltage_kv": "delivery_voltage_kv",
        }

        audit_results: List[Dict] = []
        logger.info("Running calculation engine on DB rows...")

        for _, row in df_bills.iterrows():
            bill_date = row.get("bill_date")

            # Single engine – it knows all versions for this SC from DB JSON
            engine = self.engine
            if engine is None:
                logger.warning("No tariff engine available. Skipping row.")
                continue

            engine_context: Dict = {}
            for df_col, engine_key in column_mapping.items():
                if df_col in row.index:
                    engine_context[engine_key] = row[df_col]

            # main engine call – AuditEngine should:
            #  - use service_class (sc_code) from context
            #  - select the correct logic_json block by effective_date
            calc_result = engine.calculate_expected_bill(pd.Series(engine_context))

            account_number = str(row.get("bill_account", "")).strip() or (
                str(account_id).strip() if account_id else ""
            )

            expected_val = calc_result.get("expected_bill", None)
            if expected_val is None:
                expected_val = calc_result.get("expected_amount", 0.0)

            variance_val = calc_result.get("variance", 0.0)

            audit_entry = {
                "date": row.get("bill_date"),
                "sc_code": calc_result.get("sc_code", row.get("service_class")),
                "actual": float(engine_context.get("bill_amount", 0.0)),
                "expected": float(expected_val or 0.0),
                "variance": float(variance_val or 0.0),
                "status": calc_result.get("status", "UNKNOWN"),
                "trace": calc_result.get("trace", []),
                "user_bill_id": row.get("id"),
                "bill_account": account_number,
            }
            audit_results.append(audit_entry)

        logger.info("Audit generation complete.")
        self.last_results = audit_results
        return self._format_text_report(audit_results, account_id)

    # ------------------------------------------------------------------ #
    # Text report formatting (unchanged)
    # ------------------------------------------------------------------ #

    def _format_text_report(
        self,
        results: List[Dict],
        account_id: Optional[str],
    ) -> str:
        """
        Format audit results into a text report.
        """
        if not results:
            if account_id:
                return f"No audit results generated for account_id={account_id}."
            return "No audit results generated."

        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("BILL AUDIT REPORT")
        report_lines.append("=" * 80)
        
        if account_id:
            report_lines.append(f"Account ID: {account_id}")
        else:
            report_lines.append("Account ID: ALL ACCOUNTS")
        
        report_lines.append(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        report_lines.append(f"Total Bills Audited: {len(results)}")
        report_lines.append("=" * 80)
        report_lines.append("")

        # Summary statistics
        total_variance = sum(r["variance"] for r in results)
        high_variance_count = sum(1 for r in results if abs(r["variance"]) > 0.05)
        error_count = sum(1 for r in results if r["status"] != "SUCCESS")

        report_lines.append("SUMMARY:")
        report_lines.append(f"  Total Variance: ${total_variance:.2f}")
        report_lines.append(f"  High Variance Bills (>5%): {high_variance_count}")
        report_lines.append(f"  Calculation Errors: {error_count}")
        report_lines.append("")
        report_lines.append("-" * 80)
        report_lines.append("")

        # Detailed results
        report_lines.append("DETAILED RESULTS:")
        report_lines.append("")

        for idx, result in enumerate(results, 1):
            bill_date = result.get("date")
            date_str = bill_date.strftime("%Y-%m-%d") if pd.notna(bill_date) else "N/A"
            
            report_lines.append(f"Bill #{idx}:")
            report_lines.append(f"  Date: {date_str}")
            report_lines.append(f"  Service Class: {result.get('sc_code', 'N/A')}")
            report_lines.append(f"  Account: {result.get('bill_account', 'N/A')}")
            report_lines.append(f"  Actual Amount: ${result['actual']:.2f}")
            report_lines.append(f"  Expected Amount: ${result['expected']:.2f}")
            report_lines.append(f"  Variance: ${result['variance']:.2f}")
            report_lines.append(f"  Status: {result['status']}")
            
            # Add trace information if available
            if result.get("trace"):
                report_lines.append("  Calculation Trace:")
                for trace_item in result["trace"]:
                    report_lines.append(f"    - {trace_item}")
            
            report_lines.append("")

        report_lines.append("=" * 80)
        report_lines.append("END OF REPORT")
        report_lines.append("=" * 80)

        return "\n".join(report_lines)

