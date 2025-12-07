import os
import sys
from datetime import datetime
from typing import List, Dict, Optional, Union

import pandas as pd

from src.utils.logger import get_logger
from src.utils.data_paths import get_file_path
from src.utils.helpers import clean_column_names
from src.database.db_utils import (
    insert_bill_validation_result,
    fetch_user_bills,
)

# ---- Domain logic: updated AuditEngine ------------------------------------
try:
    from src.agents.audit_calculation_agent.calc_engine_updated import AuditEngine
except ImportError as e:
    get_logger("AuditReporter").error(f"Missing domain modules: {e}")
    sys.exit(1)

logger = get_logger("AuditReporter")


class BillAuditReporter:
    """
    Wrapper around AuditEngine that can work with one or MORE tariff JSONs.

    - If a single path is passed, all bills use that engine.
    - If a list of paths is passed, we build a cache of engines and
      pick one per bill based on its bill_date (year) and, if you wish,
      the SC code / effective date pattern encoded in the filename.

    NOTE: the fine-grained effective_date logic ("read_date > effective_date"
    and "closest effective_date before read_date") should be implemented
    inside AuditEngine using the tariff definitions it loads.
    """

    def __init__(self, tariff_source: Union[str, List[str]]):
        self.last_results: List[Dict] = []

        # Map from a key (e.g., year string) -> AuditEngine
        self.engines: Dict[str, AuditEngine] = {}

        if isinstance(tariff_source, str):
            # Single JSON – keep behavior as before
            logger.info(f"Initializing BillAuditReporter with single tariff file: {tariff_source}")
            self._add_engine_for_key("default", tariff_source)

        elif isinstance(tariff_source, (list, tuple)):
            # Multiple JSON files – usually one per year / effective-date period
            logger.info(f"Initializing BillAuditReporter with multiple tariff files: {tariff_source}")
            for path in tariff_source:
                key = self._pick_engine_key_from_path(path)
                self._add_engine_for_key(key, path)

        else:
            raise ValueError("tariff_source must be a string path or a list of string paths")

    # ------------------------------------------------------------------ #
    # Engine management helpers
    # ------------------------------------------------------------------ #

    def _add_engine_for_key(self, key: str, path: str) -> None:
        """
        Create an AuditEngine for the given path and store it under 'key'.
        """
        try:
            engine = AuditEngine(path)
            self.engines[key] = engine
        except Exception as e:
            logger.error(f"Tariff file initialization failed: {path} ({e})")

    def _pick_engine_key_from_path(self, path: str) -> str:
        """
        Infer a key (typically a year) from the JSON filename.

        Example:
            'tariff_definitions_2021.json'  -> '2021'
            'sc1_2013_04_27.json'          -> '2013'  (or some other rule)

        You can customize this function to align with however you name your
        JSONs (per-year or per-effective-date).
        """
        filename = os.path.basename(path)
        # Very simple heuristic: grab the first 4-digit number as "year"
        import re

        match = re.search(r"(20\d{2})", filename)
        if match:
            return match.group(1)

        # fallback
        return "default"

    def _pick_engine_key_for_bill(self, bill_date: Optional[datetime]) -> str:
        """
        Decide which engine key to use for a bill.

        Current implementation: use bill_date.year,
        fall back to 'default' if not found.

        If you want to use effective_date windows instead of just year,
        you can:
          - store a richer key in _pick_engine_key_from_path (e.g. '2009-04-27'),
          - maintain a list of (effective_date, key) pairs, and
          - pick the key where effective_date <= bill_date and is closest.
        """
        if bill_date is None or pd.isna(bill_date):
            return "default"

        year = str(pd.to_datetime(bill_date).year)
        if year in self.engines:
            return year

        return "default"

    def _get_engine_for_bill(self, bill_date: Optional[datetime]) -> Optional[AuditEngine]:
        """
        Retrieve the appropriate AuditEngine instance for this bill.
        """
        if not self.engines:
            return None

        key = self._pick_engine_key_for_bill(bill_date)
        engine = self.engines.get(key)

        if engine is None:
            # Fallback to ANY engine (e.g., default)
            engine = self.engines.get("default")

        return engine

    # ------------------------------------------------------------------ #
    # Core: audit directly from user_bills in DB
    # ------------------------------------------------------------------ #

    def generate_audit(self, account_id: Optional[str] = None) -> str:
        """
        Pull pre-existing user_bills from DB, run the calculation engine
        appropriate for each bill (based on bill_date year / effective date),
        persist discrepancies, and generate a text report.
        """
        if not self.engines:
            return "Error: Audit Engine(s) not initialized."

        logger.info(
            f" Starting DB-based audit for account: {account_id if account_id else 'ALL ACCOUNTS'}"
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
            logger.info(
                "Service Class missing in user_bills. Defaulting to 'SC1' for all rows."
            )
            df_bills["service_class"] = "SC1"

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

        # keep a copy for potential user_bill_id matching by date
        db_bills = df_bills.copy()
        if "bill_date" in db_bills.columns:
            db_bills["bill_date"] = db_bills["bill_date"].dt.date

        for _, row in df_bills.iterrows():
            bill_date = row.get("bill_date")

            # 🔑 Pick the right engine based on this bill's date (and implicitly its year/effective date)
            engine = self._get_engine_for_bill(bill_date)
            if engine is None:
                logger.warning(f"No tariff engine available for bill_date={bill_date}. Skipping row.")
                continue

            engine_context: Dict = {}
            for df_col, engine_key in column_mapping.items():
                if df_col in row.index:
                    engine_context[engine_key] = row[df_col]

            # main engine call – AuditEngine itself should:
            #  - detect the sc_code
            #  - choose the right effective_date logic where read_date > effective_date
            #  - if multiple effective dates, pick the closest one <= read_date
            calc_result = engine.calculate_expected_bill(pd.Series(engine_context))

            # account_id per row
            account_number = str(row.get("bill_account", "")).strip() or (
                str(account_id).strip() if account_id else ""
            )

            # expected value: prefer expected_bill, fallback to expected_amount if needed
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
                # keep DB identifiers for linking
                "user_bill_id": row.get("id"),
                "bill_account": account_number,
            }
            audit_results.append(audit_entry)

            # persist validation result if variance or status suspicious
            if abs(audit_entry["variance"]) > 0.05 or audit_entry["status"] != "SUCCESS":
                self._persist_validation_result(audit_entry, account_number, db_bills)

        logger.info("Audit generation complete.")
        self.last_results = audit_results
        return self._format_text_report(audit_results, account_id)

    # ------------------------------------------------------------------ #
    # DB writeback: BillValidationResult
    # ------------------------------------------------------------------ #

    def _persist_validation_result(
        self,
        entry: Dict,
        account_id: str,
        db_bills: pd.DataFrame,
    ):
        """
        Helper to save discrepancy to DB using db_utils.
        """
        user_bill_id = entry.get("user_bill_id")

        # If user_bill_id not already present, try to match by bill_date
        if not user_bill_id and not db_bills.empty:
            entry_date = (
                pd.to_datetime(entry["date"]).date()
                if entry["date"] is not None
                else None
            )
            if entry_date:
                match = db_bills[db_bills["bill_date"] == entry_date]
                if not match.empty and "id" in match.columns:
                    user_bill_id = int(match.iloc[0]["id"])

        issue_type = (
            "High Variance"
            if entry["status"] == "SUCCESS"
            else "Calculation Error or Skipped"
        )

        record = {
            "user_bill_id": user_bill_id,  # Can be None if link fails
            "account_id": account_id,
            "issue_type": issue_type,
            "description": (
                f"Variance: ${entry['variance']:.2f}. "
                f"Actual: ${entry['actual']:.2f}, Expected: ${entry['expected']:.2f}. "
                f"Status: {entry['status']}"
            ),
            "status": "open",
            "detected_on": datetime.utcnow(),
        }

        insert_bill_validation_result(record)

    # ------------------------------------------------------------------ #
    # Text report formatting (unchanged)
    # ------------------------------------------------------------------ #

    def _format_text_report(
        self,
        results: List[Dict],
        account_id: Optional[str],
    ) -> str:
        ...
        # (keep your existing implementation unchanged)
        ...

