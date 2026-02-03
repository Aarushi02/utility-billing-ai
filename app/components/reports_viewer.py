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
    get_engine,
)
from src.agents.reporting_generating_agent.report_generator import BillAuditReporter

try:
    from src.agents.audit_calculation_agent.calc_engine_updated import AuditEngine
except Exception:
    AuditEngine = None

logger = get_logger("AuditReportViewer")

# ---------------------------------------------------------
# Allowed Service Classifications (UI only)
# ---------------------------------------------------------
ALLOWED_SC_MAP = {
    "SC-1": "SC1",
    "SC-1C": "SC1C",
    "SC-2 ND": "SC2",    # non-demand
    "SC-2": "SC2D",     # demand
    "SC-3": "SC3",
    "SC-3A": "SC3A",
}

# ---------------------------------------------------------
# Excel helpers
# ---------------------------------------------------------
def _safe_excel_sheet_name(name: str, fallback: str = "Audit Results") -> str:
    if not name:
        return fallback
    name = re.sub(r"[:\\/?*\[\]]", " ", str(name))
    name = re.sub(r"\s+", " ", name).strip()[:31]
    return name or fallback


def _df_to_excel_bytes(df: pd.DataFrame, sheet_name: str) -> BytesIO:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=_safe_excel_sheet_name(sheet_name))
    buf.seek(0)
    return buf


# ---------------------------------------------------------
# Grid helpers
# ---------------------------------------------------------
def _clean_column_names_local(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [
        re.sub(r"[^a-z0-9_]+", "_", str(c).strip().lower()).strip("_")
        for c in df.columns
    ]
    return df


def _resolve_bill_grid_columns(df: pd.DataFrame) -> dict | None:
    def pick(cols):
        for c in cols:
            if c in df.columns:
                return c
        return None

    bill_date = pick(["read_date", "bill_date", "date"])
    kwh = pick(["billed_kwh", "kwh", "usage_kwh"])
    demand = pick(["billed_demand", "demand_kw", "kw_demand"])
    amount = pick(["bill_amount", "total_bill", "current_charges"])

    if not all([bill_date, kwh, demand, amount]):
        return None

    return {
        "bill_date": bill_date,
        "billed_kwh": kwh,
        "billed_demand": demand,
        "bill_amount": amount,
    }


def _build_bill_override_grid(df: pd.DataFrame, cols: dict, sc: str) -> pd.DataFrame:
    out = df[[cols["bill_date"], cols["billed_kwh"], cols["billed_demand"], cols["bill_amount"]]].copy()
    out["service_class"] = sc
    out["override_tra"] = 0.0
    out["override_rdm"] = 0.0
    return out


def _compute_expected_from_overrides(engine, grid_df, cols):
    rows = []

    for _, r in grid_df.iterrows():
        ctx = {
            "read_date": r[cols["bill_date"]],
            "bill_date": r[cols["bill_date"]],
            "billed_kwh": r[cols["billed_kwh"]],
            "billed_demand": r[cols["billed_demand"]],
            "bill_amount": r[cols["bill_amount"]],
            "service_class": r["service_class"],
            "override_tra": r["override_tra"],
            "override_rdm": r["override_rdm"],
        }

        out = engine.calculate_expected_bill(pd.Series(ctx))

        rows.append({
            "Bill Date": ctx["bill_date"],
            "Service Class": out.get("sc_code"),
            "kWh": float(ctx["billed_kwh"]),
            "Demand (kW)": float(ctx["billed_demand"]),
            "Actual Bill": float(ctx["bill_amount"]),
            "TRA": float(ctx["override_tra"]),
            "RDM": float(ctx["override_rdm"]),
            "Expected Bill": out.get("expected_bill", 0.0),
            "Variance": out.get("variance", 0.0),
            "Status": out.get("status"),
        })

    df = pd.DataFrame(rows)
    df["Expected Bill"] = df["Expected Bill"].round(2)
    df["Actual Bill"] = df["Actual Bill"].round(2)
    df["Variance"] = df["Variance"].round(2)
    return df


# ---------------------------------------------------------
# Tariff JSON builder
# ---------------------------------------------------------
def _build_tariff_json_from_db_for_account(account_id: str, sc_code: str) -> str:
    engine = get_engine()
    with engine.begin() as conn:
        rows = conn.execute(
            text("""
                SELECT logic_json, effective_date, end_date
                FROM tariff_logic_versions
                WHERE sc_code = :sc
                ORDER BY effective_date
            """),
            {"sc": sc_code},
        ).mappings().all()

    defs = []
    for r in rows:
        obj = json.loads(r["logic_json"])
        obj.setdefault("metadata", {})["sc_code"] = sc_code
        defs.append(obj)

    fd, path = tempfile.mkstemp(prefix=f"tariff_{sc_code}_{account_id}_", suffix=".json")
    with os.fdopen(fd, "w") as f:
        json.dump(defs, f, indent=2)

    return path


# ---------------------------------------------------------
# MAIN VIEW
# ---------------------------------------------------------
def render_report_viewer():
    st.title("Audit Report Viewer")

    if "run_override_calc" not in st.session_state:
        st.session_state.run_override_calc = False

    accounts = fetch_user_bills(None)["bill_account"].dropna().unique().tolist()
    account = st.selectbox("Account Number", accounts)

    sc_label = st.selectbox("Service Classification", list(ALLOWED_SC_MAP.keys()))
    sc_code = ALLOWED_SC_MAP[sc_label]

    tariff_path = _build_tariff_json_from_db_for_account(account, sc_code)

    df = fetch_user_bills(account_id=account)
    df = _clean_column_names_local(df)
    df = df[df["service_class"].str.upper().str.replace("-", "") == sc_code]

    cols = _resolve_bill_grid_columns(df)
    if not cols:
        st.error("Required bill columns missing.")
        return

    grid_key = f"override_grid_{account}_{sc_code}"
    if grid_key not in st.session_state:
        st.session_state[grid_key] = _build_bill_override_grid(df, cols, sc_code)

    st.subheader("Expected Bill Calculator (TRA / RDM Overrides)")

    edited = st.data_editor(
        st.session_state[grid_key],
        num_rows="fixed",
        use_container_width=True,
        column_config={
            "override_tra": st.column_config.NumberColumn("TRA ($/kWh)", format="%.5f"),
            "override_rdm": st.column_config.NumberColumn("RDM ($/unit)", format="%.2f"),
        },
    )

    st.session_state[grid_key] = edited
    st.session_state.run_override_calc = False

    if st.button("Calculate Expected Bill", type="primary"):
        st.session_state.run_override_calc = True

    if st.session_state.run_override_calc:
        engine = AuditEngine(tariff_path)
        result_df = _compute_expected_from_overrides(engine, edited, cols)

        st.dataframe(result_df, use_container_width=True)

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Actual", f"${result_df['Actual Bill'].sum():,.2f}")
        c2.metric("Total Expected", f"${result_df['Expected Bill'].sum():,.2f}")
        c3.metric("Total Variance", f"${result_df['Variance'].sum():,.2f}")

        st.download_button(
            "Download Expected Bill (Excel)",
            data=_df_to_excel_bytes(result_df, f"{sc_code}_Overrides"),
            file_name=f"expected_bill_{account}_{sc_code}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


if __name__ == "__main__":
    render_report_viewer()
