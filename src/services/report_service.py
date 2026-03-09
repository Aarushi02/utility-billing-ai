import json
import os
import re
import tempfile

import pandas as pd
from sqlalchemy import bindparam, text

from src.agents.Variable_Updates.extra_charges import store_override_values
from src.agents.audit_calculation_agent.calc_engine_updated import AuditEngine
from src.database.db_utils import get_engine
from src.database.utils.user_bills_utils import fetch_user_bills
from src.database.utils.variables_tariff_rates import fetch_rates_for_dates


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
    
    def fetch_override_values(self, sc_code: str, bill_dates: list):
        if not bill_dates:
            return pd.DataFrame()

        query = text("""
            SELECT bill_date, override_tra, override_rdm, override_sbc, override_ram
            FROM override_values
            WHERE sc_code = :sc_code
            AND bill_date IN :dates
        """).bindparams(bindparam("dates", expanding=True))

        with self.engine.begin() as conn:
            rows = conn.execute(
            query,
            {"sc_code": sc_code, "dates": bill_dates},
            ).mappings().all()

        return pd.DataFrame(rows)

    def load_override_grid(self, sc_code: str) -> list[dict]:

        df = fetch_user_bills()   # no account filter
        df = self._clean_columns(df)

        sc_column = self._resolve_service_class_column(df)

        if sc_column:
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
            "bill_date": pd.to_datetime(
                df[cols["bill_date"]], errors="coerce"
            ).dt.strftime("%Y-%m-%d"),

            "billed_kwh": pd.to_numeric(
                df[cols["billed_kwh"]], errors="coerce"
            ).fillna(0.0),

            "billed_demand": pd.to_numeric(
                df[cols["billed_demand"]], errors="coerce"
            ).fillna(0.0),

            "bill_amount": pd.to_numeric(
                df[cols["bill_amount"]], errors="coerce"
            ).fillna(0.0),
        })

        grid = grid.dropna(subset=["bill_date"]).copy()
        grid["service_class"] = sc_code

        bill_dates = grid["bill_date"].tolist()

        # fetch stored tariff overrides
        tra_rows = fetch_rates_for_dates("tra", sc_code, bill_dates)
        rdm_rows = fetch_rates_for_dates("rdm", sc_code, bill_dates)
        sbc_rows = fetch_rates_for_dates("sbc", sc_code, bill_dates)
        ram_rows = fetch_rates_for_dates("ram", sc_code, bill_dates)

        tra_df = pd.DataFrame(tra_rows)
        rdm_df = pd.DataFrame(rdm_rows)
        sbc_df = pd.DataFrame(sbc_rows)
        ram_df = pd.DataFrame(ram_rows)

        if not tra_df.empty:
            tra_df = tra_df.rename(columns={"effective_date": "bill_date", "rate": "override_tra"})

        if not rdm_df.empty:
            rdm_df = rdm_df.rename(columns={"effective_date": "bill_date", "rate": "override_rdm"})

        if not sbc_df.empty:
            sbc_df = sbc_df.rename(columns={"effective_date": "bill_date", "rate": "override_sbc"})

        if not ram_df.empty:
            ram_df = ram_df.rename(columns={"effective_date": "bill_date", "rate": "override_ram"})

        for rate_df in [tra_df, rdm_df, sbc_df, ram_df]:
            if not rate_df.empty:
                grid = grid.merge(rate_df, on="bill_date", how="left")

        for col in ["override_tra", "override_rdm", "override_sbc", "override_ram"]:
            if col not in grid.columns:
                grid[col] = None
            else:
                grid[col] = pd.to_numeric(grid[col], errors="coerce")

        return grid.to_dict("records")

    def calculate_expected_bill(self, account_id: str, sc_code: str, rows: list[dict]) -> dict:
        grid_df = pd.DataFrame(rows)
        if grid_df.empty:
            return {"rows": [], "total_actual": 0.0, "total_expected": 0.0, "total_variance": 0.0}

        for column in ["billed_kwh", "billed_demand", "bill_amount", "override_tra", "override_rdm"]:
            if column in grid_df.columns:
                grid_df[column] = pd.to_numeric(grid_df[column], errors="coerce").fillna(0.0)

        if "service_class" not in grid_df.columns:
            grid_df["service_class"] = sc_code

        store_override_values(grid_df, bill_date_col="bill_date")

        tariff_path = self._build_tariff_json_from_db(account_id=account_id, sc_code=sc_code)
        try:
            audit_engine = AuditEngine(tariff_path)
            result_rows = []

            for _, row in grid_df.iterrows():
                ctx = {
                    "read_date": row.get("bill_date"),
                    "bill_date": row.get("bill_date"),
                    "billed_kwh": float(row.get("billed_kwh", 0.0)),
                    "billed_demand": float(row.get("billed_demand", 0.0)),
                    "bill_amount": float(row.get("bill_amount", 0.0)),
                    "service_class": row.get("service_class", sc_code),
                    "override_tra": float(row.get("override_tra", 0.0)),
                    "override_rdm": float(row.get("override_rdm", 0.0)),
                }

                out = audit_engine.calculate_expected_bill(pd.Series(ctx))
                result_rows.append(
                    {
                        "bill_date": str(ctx["bill_date"]),
                        "service_class": out.get("sc_code", sc_code),
                        "kwh": float(ctx["billed_kwh"]),
                        "demand_kw": float(ctx["billed_demand"]),
                        "actual_bill": round(float(ctx["bill_amount"]), 2),
                        "tra": float(ctx["override_tra"]),
                        "rdm": float(ctx["override_rdm"]),
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
