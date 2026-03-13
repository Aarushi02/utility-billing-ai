import json
import os
import re
import tempfile

import pandas as pd
import math
import numpy as np

from sqlalchemy import bindparam, text

from src.agents.Variable_Updates.extra_charges import store_override_values
from src.agents.audit_calculation_agent.calc_engine_updated import AuditEngine
from src.database.db_utils import get_engine
from src.database.utils.user_bills_utils import fetch_user_bills
from src.database.utils.variables_tariff_rates import fetch_rates_for_dates
from src.database.utils.variables_tariff_rates import (
    insert_tra_rate,
    insert_rdm_rate,
    insert_sbc_rate,
    insert_ram_rate,
)


class ReportService:
    def __init__(self) -> None:
        self.engine = get_engine()

    @staticmethod
    def _clean_columns(df: pd.DataFrame) -> pd.DataFrame:
        data = df.copy()
        data.columns = [
            re.sub(r"[^a-z0-9_]+", "_", str(column).lower()).strip("_")
            for column in data.columns
        ]
        return data

    @staticmethod
    def _resolve_service_class_column(df: pd.DataFrame) -> str | None:
        for column in [
            "service_class",
            "rate_class",
            "sc_code",
            "serviceclassification",
            "service_classification",
        ]:
            if column in df.columns:
                return column
        return None

    @staticmethod
    def _resolve_bill_columns(df: pd.DataFrame) -> dict | None:
        def pick(candidates: list[str]) -> str | None:
            for candidate in candidates:
                if candidate in df.columns:
                    return candidate
            return None

        bill_date = pick(["read_date", "bill_date", "date"])
        billed_kwh = pick(["billed_kwh", "kwh", "usage_kwh", "energy_kwh"])
        billed_demand = pick(["billed_demand", "demand_kw", "kw_demand"])
        bill_amount = pick(["bill_amount", "total_bill", "current_charges", "amount_due"])

        if not all([bill_date, billed_kwh, billed_demand, bill_amount]):
            return None

        return {
            "bill_date": bill_date,
            "billed_kwh": billed_kwh,
            "billed_demand": billed_demand,
            "bill_amount": bill_amount,
        }

    def list_accounts(self) -> list[str]:
        all_bills = fetch_user_bills()
        if all_bills is None or all_bills.empty:
            return []
        all_bills = self._clean_columns(all_bills)
        if "bill_account" not in all_bills.columns:
            return []
        return sorted(all_bills["bill_account"].dropna().astype(str).unique().tolist())
    
    def load_override_grid(self, sc_code: str) -> list[dict]:
        df = fetch_user_bills()
        if df is None or df.empty:
            return []

        df = self._clean_columns(df)

        sc_column = self._resolve_service_class_column(df)
        if sc_column and sc_code:
            normalized_target = str(sc_code).upper().replace("-", "")
            df = df[
                df[sc_column]
                .astype(str)
                .str.upper()
                .str.replace("-", "", regex=False)
                == normalized_target
            ].copy()

        cols = self._resolve_bill_columns(df)
        if not cols:
            return []

        grid = pd.DataFrame({
            "bill_date": pd.to_datetime(df[cols["bill_date"]], errors="coerce").dt.strftime("%Y-%m-%d"),
            "billed_kwh": pd.to_numeric(df[cols["billed_kwh"]], errors="coerce"),
            "billed_demand": pd.to_numeric(df[cols["billed_demand"]], errors="coerce"),
            "bill_amount": pd.to_numeric(df[cols["bill_amount"]], errors="coerce"),
        })

        grid = grid.dropna(subset=["bill_date"]).copy()
        if grid.empty:
            return []

        grid["bill_date"] = grid["bill_date"].astype(str)
        grid["service_class"] = sc_code

        bill_dates = grid["bill_date"].tolist()

        tra_map = {
            row["effective_date"]: row["rate"]
            for row in fetch_rates_for_dates("tra", sc_code, bill_dates)
        }
        rdm_map = {
            row["effective_date"]: row["rate"]
            for row in fetch_rates_for_dates("rdm", sc_code, bill_dates)
        }
        sbc_map = {
            row["effective_date"]: row["rate"]
            for row in fetch_rates_for_dates("sbc", sc_code, bill_dates)
        }
        ram_map = {
            row["effective_date"]: row["rate"]
            for row in fetch_rates_for_dates("ram", sc_code, bill_dates)
        }

        grid["override_tra"] = grid["bill_date"].map(tra_map)
        grid["override_rdm"] = grid["bill_date"].map(rdm_map)
        grid["override_sbc"] = grid["bill_date"].map(sbc_map)
        grid["override_ram"] = grid["bill_date"].map(ram_map)

        numeric_cols = [
            "billed_kwh",
            "billed_demand",
            "bill_amount",
            "override_tra",
            "override_rdm",
            "override_sbc",
            "override_ram",
        ]

        for col in numeric_cols:
            grid[col] = pd.to_numeric(grid[col], errors="coerce")

        # for UI only
        display_cols = ["override_tra", "override_rdm", "override_sbc", "override_ram"]
        for col in display_cols:
            grid[col] = grid[col].fillna(0.0)

        records = grid.to_dict(orient="records")
        return records
    
        
            
    def calculate_expected_bill(self, account_id: str, sc_code: str, rows: list[dict]) -> dict:
        grid_df = pd.DataFrame(rows)
        if grid_df.empty:
            return {
                "rows": [],
                "total_actual": 0.0,
                "total_expected": 0.0,
                "total_variance": 0.0,
            }

        for column in [
            "billed_kwh",
            "billed_demand",
            "bill_amount",
            "override_tra",
            "override_rdm",
            "override_sbc",
            "override_ram",
        ]:
            if column in grid_df.columns:
                grid_df[column] = pd.to_numeric(grid_df[column], errors="coerce")

        if "service_class" not in grid_df.columns:
            grid_df["service_class"] = sc_code

        tariff_path = self._build_tariff_json_from_db(account_id=account_id, sc_code=sc_code)

        try:
            audit_engine = AuditEngine(tariff_path)
            result_rows = []

            for _, row in grid_df.iterrows():
                ctx = {
                    "read_date": row.get("bill_date"),
                    "bill_date": row.get("bill_date"),
                    "billed_kwh": float(row.get("billed_kwh") or 0.0),
                    "billed_demand": float(row.get("billed_demand") or 0.0),
                    "bill_amount": float(row.get("bill_amount") or 0.0),
                    "service_class": row.get("service_class", sc_code),
                    "override_tra": None if pd.isna(row.get("override_tra")) else float(row.get("override_tra")),
                    "override_rdm": None if pd.isna(row.get("override_rdm")) else float(row.get("override_rdm")),
                    "override_sbc": None if pd.isna(row.get("override_sbc")) else float(row.get("override_sbc")),
                    "override_ram": None if pd.isna(row.get("override_ram")) else float(row.get("override_ram")),
                }

                out = audit_engine.calculate_expected_bill(pd.Series(ctx))

                result_rows.append(
                    {
                        "bill_date": str(ctx["bill_date"]),
                        "service_class": out.get("sc_code", sc_code),
                        "kwh": float(ctx["billed_kwh"]),
                        "demand_kw": float(ctx["billed_demand"]),
                        "actual_bill": round(float(ctx["bill_amount"]), 2),
                        "tra": 0.0 if ctx["override_tra"] is None else float(ctx["override_tra"]),
                        "rdm": 0.0 if ctx["override_rdm"] is None else float(ctx["override_rdm"]),
                        "expected_bill": round(float(out.get("expected_bill", 0.0)), 2),
                        "variance": round(float(out.get("variance", 0.0)), 2),
                        "status": out.get("status", "SUCCESS"),
                    }
                )

            result_df = pd.DataFrame(result_rows)

            return {
                "rows": result_rows,
                "total_actual": round(float(result_df["actual_bill"].sum()), 2),
                "total_expected": round(float(result_df["expected_bill"].sum()), 2),
                "total_variance": round(float(result_df["variance"].sum()), 2),
            }
        finally:
            try:
                os.remove(tariff_path)
            except OSError:
                pass

    def _build_tariff_json_from_db(self, account_id: str, sc_code: str) -> str:
        with self.engine.begin() as connection:
            rows = connection.execute(
                text(
                    """
                    SELECT logic_json
                    FROM tariff_logic_versions
                    WHERE sc_code = :sc_code
                    ORDER BY effective_date
                    """
                ),
                {"sc_code": sc_code},
            ).mappings().all()

        if not rows:
            raise RuntimeError(f"No tariff logic found for sc_code={sc_code}")

        definitions = []
        for row in rows:
            raw = row["logic_json"]
            if isinstance(raw, str):
                obj = json.loads(raw)
            elif isinstance(raw, dict):
                obj = raw
            else:
                continue
            obj.setdefault("metadata", {})
            obj["metadata"].setdefault("sc_code", sc_code)
            definitions.append(obj)

        fd, path = tempfile.mkstemp(prefix=f"tariff_{sc_code}_{account_id}_", suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as file_handle:
            json.dump(definitions, file_handle, indent=2)
        return path
 

    def save_overrides(self, sc_code: str, rows: list[dict]) -> dict:
        saved = {"TRA": 0, "RDM": 0, "SBC": 0, "RAM": 0}

        for row in rows:
            bill_date = row.get("bill_date")

            tra = row.get("override_tra")
            if tra is not None and not pd.isna(tra) and float(tra) != 0.0:
                print("SAVING TRA:", bill_date, sc_code, tra)
                if insert_tra_rate(
                    {
                        "effective_date": bill_date,
                        "sc_code": sc_code,
                        "rate": float(tra),
                    }
                ):
                    saved["TRA"] += 1

            rdm = row.get("override_rdm")
            if rdm is not None and not pd.isna(rdm) and float(rdm) != 0.0:
                print("SAVING RDM:", bill_date, sc_code, rdm)
                if insert_rdm_rate(
                    {
                        "effective_date": bill_date,
                        "sc_code": sc_code,
                        "rate": float(rdm),
                    }
                ):
                    saved["RDM"] += 1

            sbc = row.get("override_sbc")
            if sbc is not None and not pd.isna(sbc) and float(sbc) != 0.0:
                if insert_sbc_rate(
                    {
                        "effective_date": bill_date,
                        "sc_code": sc_code,
                        "rate": float(sbc),
                    }
                ):
                    saved["SBC"] += 1

            ram = row.get("override_ram")
            if ram is not None and not pd.isna(ram) and float(ram) != 0.0:
                if insert_ram_rate(
                    {
                        "effective_date": bill_date,
                        "sc_code": sc_code,
                        "rate": float(ram),
                    }
                ):
                    saved["RAM"] += 1

        print("SAVE COUNTS:", saved)
        return saved