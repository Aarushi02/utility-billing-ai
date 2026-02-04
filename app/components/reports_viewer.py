import os
import re
import json
import tempfile
from io import BytesIO

import pandas as pd
import streamlit as st
from sqlalchemy import text

from src.utils.logger import get_logger
from src.database.db_utils import get_engine
from src.database.utils.user_bills_utils import fetch_user_bills

try:
    from src.agents.audit_calculation_agent.calc_engine_updated import AuditEngine
except Exception:
    AuditEngine = None

logger = get_logger("AuditReportViewer")

# =========================================================
# CONSTANTS
# =========================================================

ALLOWED_SC_MAP = {
    "SC-1": "SC1",
    "SC-1C": "SC1C",
    "SC-2 ND": "SC2",
    "SC-2": "SC2D",
    "SC-3": "SC3",
    "SC-3A": "SC3A",
}

# =========================================================
# SAFE HELPERS
# =========================================================

def _clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [
        re.sub(r"[^a-z0-9_]+", "_", str(c).lower()).strip("_")
        for c in df.columns
    ]
    return df


def _safe_excel_sheet_name(name: str) -> str:
    name = re.sub(r"[:\\/?*\[\]]", " ", str(name))
    return re.sub(r"\s+", " ", name).strip()[:31] or "Results"


def _df_to_excel_bytes(df: pd.DataFrame, sheet_name: str) -> BytesIO:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=_safe_excel_sheet_name(sheet_name))
    buf.seek(0)
    return buf


# =========================================================
# COLUMN RESOLUTION (NO ASSUMPTIONS)
# =========================================================

def _resolve_service_class_column(df: pd.DataFrame) -> str | None:
    for c in [
        "service_class",
        "rate_class",
        "sc_code",
        "serviceclassification",
        "service_classification",
    ]:
        if c in df.columns:
            return c
    return None


def _resolve_bill_columns(df: pd.DataFrame) -> dict | None:
    def pick(candidates):
        for c in candidates:
            if c in df.columns:
                return c
        return None

    bill_date = pick(["read_date", "bill_date", "date"])
    kwh = pick(["billed_kwh", "kwh", "usage_kwh", "energy_kwh"])
    demand = pick(["billed_demand", "demand_kw", "kw_demand"])
    amount = pick(["bill_amount", "total_bill", "current_charges", "amount_due"])

    if not all([bill_date, kwh, demand, amount]):
        return None

    return {
        "bill_date": bill_date,
        "billed_kwh": kwh,
        "billed_demand": demand,
        "bill_amount": amount,
    }


# =========================================================
# GRID + TARIFF HELPERS
# =========================================================

def _build_override_grid(df: pd.DataFrame, cols: dict, sc_code: str) -> pd.DataFrame:
    out = df[
        [
            cols["bill_date"],
            cols["billed_kwh"],
            cols["billed_demand"],
            cols["bill_amount"],
        ]
    ].copy()

    out["service_class"] = sc_code
    out["override_tra"] = 0.0
    out["override_rdm"] = 0.0
    return out


def _build_tariff_json_from_db(account_id: str, sc_code: str) -> str:
    engine = get_engine()

    with engine.begin() as conn:
        rows = conn.execute(
            text("""
                SELECT logic_json
                FROM tariff_logic_versions
                WHERE sc_code = :sc
                ORDER BY effective_date
            """),
            {"sc": sc_code},
        ).mappings().all()

    if not rows:
        raise RuntimeError(f"No tariff logic found for SC={sc_code}")

    definitions = []

    for r in rows:
        raw = r["logic_json"]

        if isinstance(raw, str):
            obj = json.loads(raw)
        elif isinstance(raw, dict):
            obj = raw
        else:
            continue

        obj.setdefault("metadata", {})
        obj["metadata"].setdefault("sc_code", sc_code)
        definitions.append(obj)

    fd, path = tempfile.mkstemp(
        prefix=f"tariff_{sc_code}_{account_id}_",
        suffix=".json"
    )

    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(definitions, f, indent=2)

    return path


def _compute_expected(engine, grid_df, cols):
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
    df[["Expected Bill", "Actual Bill", "Variance"]] = df[
        ["Expected Bill", "Actual Bill", "Variance"]
    ].round(2)

    return df


# =========================================================
# SAFE SESSION STATE UPDATE (CRITICAL FIX)
# =========================================================

def _safe_update_grid_state(grid_key: str, edited_df: pd.DataFrame):
    prev_df = st.session_state.get(grid_key)

    if prev_df is None:
        st.session_state[grid_key] = edited_df
        return

    try:
        if not edited_df.equals(prev_df):
            st.session_state[grid_key] = edited_df
            st.session_state.run_override_calc = False
    except Exception:
        st.session_state[grid_key] = edited_df
        st.session_state.run_override_calc = False


# =========================================================
# MAIN VIEW
# =========================================================

def render_report_viewer():

    # ---- SESSION STATE (MUST BE FIRST) ----
    st.session_state.setdefault("run_override_calc", False)

    st.title("Audit Report Viewer")

    # ---- LOAD ALL BILLS ----
    all_bills = fetch_user_bills(account_id=None)
    if all_bills is None or all_bills.empty:
        st.error("No billing data available.")
        return

    all_bills = _clean_columns(all_bills)

    if "bill_account" not in all_bills.columns:
        st.error("Missing bill_account column.")
        return

    accounts = sorted(all_bills["bill_account"].dropna().unique())
    account = st.selectbox("Account Number", accounts)

    # ---- SERVICE CLASS ----
    sc_label = st.selectbox("Service Classification", list(ALLOWED_SC_MAP.keys()))
    sc_code = ALLOWED_SC_MAP[sc_label]

    # ---- BUILD TARIFF ----
    tariff_path = _build_tariff_json_from_db(account, sc_code)

    # ---- LOAD ACCOUNT BILLS ----
    df = fetch_user_bills(account_id=account)
    df = _clean_columns(df)

    sc_col = _resolve_service_class_column(df)
    if sc_col:
        df = df[
            df[sc_col]
            .astype(str)
            .str.upper()
            .str.replace("-", "", regex=False)
            == sc_code
        ].copy()

    cols = _resolve_bill_columns(df)
    if not cols:
        st.error("Required billing columns not found.")
        return

    grid_key = f"override_grid_{account}_{sc_code}"
    if grid_key not in st.session_state:
        st.session_state[grid_key] = _build_override_grid(df, cols, sc_code)

    # ---- DATA EDITOR ----
    st.subheader("Expected Bill Calculator (TRA / RDM Overrides)")

    edited = st.data_editor(
        st.session_state[grid_key],
        num_rows="fixed",
        use_container_width=True,
        column_config={
            "override_tra": st.column_config.NumberColumn(
                "TRA ($/kWh)", format="%.5f", step=0.00001
            ),
            "override_rdm": st.column_config.NumberColumn(
                "RDM ($/unit)", format="%.2f", step=0.01
            ),
        },
    )

    _safe_update_grid_state(grid_key, edited)

    st.caption("Tip: Press Enter or click outside the cell to commit a value.")

    if st.button("Calculate Expected Bill", type="primary"):
        st.session_state.run_override_calc = True

    # ---- CALCULATION ----
    if st.session_state.run_override_calc:
        engine = AuditEngine(tariff_path)
        result_df = _compute_expected(engine, st.session_state[grid_key], cols)

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
