from io import BytesIO
import re
import time

import pandas as pd
import requests
import streamlit as st

from src.utils.config import get_env


ALLOWED_SC_MAP = {
    "SC-1": "SC1",
    "SC-1C": "SC1C",
    "SC-2 ND": "SC2",
    "SC-2": "SC2D",
    "SC-3": "SC3",
    "SC-3A": "SC3A",
}

API_BASE_URL = get_env("API_BASE_URL", "http://localhost:8000")


DISPLAY_COL_MAP = {
    "bill_date": "Bill Date",
    "service_class": "Service Class",
    "kwh": "kWh",
    "demand_kw": "Demand (kW)",
    "actual_bill": "Actual Bill",
    "tra": "TRA",
    "rdm": "RDM",
    "expected_bill": "Expected Bill",
    "variance": "Variance",
    "status": "Status",
}


def _safe_excel_sheet_name(name: str) -> str:
    name = re.sub(r"[:\\/?*\[\]]", " ", str(name))
    return re.sub(r"\s+", " ", name).strip()[:31] or "Results"


def _df_to_excel_bytes(df: pd.DataFrame, sheet_name: str) -> BytesIO:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=_safe_excel_sheet_name(sheet_name))
    buffer.seek(0)
    return buffer


def _get_api_json(path: str, params: dict | None = None):
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            response = requests.get(f"{API_BASE_URL}{path}", params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            last_exc = exc
            if attempt < 2:
                time.sleep(1 + attempt)
                continue
            raise

    if last_exc:
        raise last_exc


def _post_api_json(path: str, payload: dict):
    response = requests.post(f"{API_BASE_URL}{path}", json=payload, timeout=60)
    response.raise_for_status()
    return response.json()


def _result_to_display_df(rows: list[dict]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    result_df = pd.DataFrame(rows)
    result_df = result_df.rename(columns=DISPLAY_COL_MAP)
    return result_df


def _normalize_grid_df(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()

    for col in ["override_tra", "override_rdm", "override_sbc", "override_ram"]:
        if col not in out.columns:
            out[col] = 0.0
        else:
            out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0.0)

    for col in ["billed_kwh", "billed_demand", "bill_amount"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0.0)

    return out


def render_report_viewer():
    st.session_state.setdefault("run_override_calc", False)

    st.title("Audit Report Viewer")

    try:
        accounts = _get_api_json("/api/v1/reports/accounts").get("accounts", [])
    except requests.RequestException as exc:
        st.error(f"Unable to load accounts from API: {exc}")
        return

    if not accounts:
        st.error("No billing data available.")
        return

    account = st.selectbox("Account Number", accounts)
    sc_label = st.selectbox("Service Classification", list(ALLOWED_SC_MAP.keys()))
    sc_code = ALLOWED_SC_MAP[sc_label]

    grid_key = f"override_grid_{account}_{sc_code}"
    selection_key = "report_selection_key"
    current_selection = (account, sc_code)
    previous_selection = st.session_state.get(selection_key)

    # Load grid from API only when account / service class changes
    if previous_selection != current_selection or grid_key not in st.session_state:
        try:
            rows = _get_api_json(
                "/api/v1/reports/grid",
                params={"account_id": account, "sc_code": sc_code},
            ).get("rows", [])
        except requests.RequestException as exc:
            st.error(f"Unable to load override grid from API: {exc}")
            return

        if not rows:
            st.error("Required billing columns not found.")
            return

        df = pd.DataFrame(rows)
        st.session_state[grid_key] = _normalize_grid_df(df)
        st.session_state[selection_key] = current_selection
        st.session_state.run_override_calc = False

    st.subheader("Expected Bill Calculator (TRA / RDM Overrides)")

    edited = st.data_editor(
        st.session_state[grid_key],
        key=f"editor_{account}_{sc_code}",
        num_rows="fixed",
        use_container_width=True,
        column_config={
            "override_tra": st.column_config.NumberColumn(
                "TRA ($/kWh)", format="%.5f", step=0.00001
            ),
            "override_rdm": st.column_config.NumberColumn(
                "RDM ($/unit)", format="%.5f", step=0.00001
            ),
            "override_sbc": st.column_config.NumberColumn(
                "SBC ($/unit)", format="%.5f", step=0.00001
            ),
            "override_ram": st.column_config.NumberColumn(
                "RAM ($/unit)", format="%.5f", step=0.00001
            ),
        },
    )

    # Only update local session state here. Do not save yet.
    st.session_state[grid_key] = _normalize_grid_df(edited)

    st.caption("Edit all values first, then click Save Overrides.")

    c1, c2 = st.columns(2)

    with c1:
        if st.button("Save Overrides", type="primary", use_container_width=True):
            payload_rows = st.session_state[grid_key].to_dict(orient="records")

            try:
                result = _post_api_json(
                    "/api/v1/reports/save-overrides",
                    {
                        "account_id": account,
                        "sc_code": sc_code,
                        "rows": payload_rows,
                    },
                )
            except requests.RequestException as exc:
                st.error(f"Unable to save overrides to API: {exc}")
                return

            refreshed_rows = result.get("rows", [])
            refreshed_df = pd.DataFrame(refreshed_rows)

            st.session_state[grid_key] = _normalize_grid_df(refreshed_df)

            # Force one clean reload cycle next run so UI and API stay in sync
            st.session_state[selection_key] = None

            st.success("Overrides saved successfully.")
            st.rerun()

    with c2:
        if st.button("Calculate Expected Bill", use_container_width=True):
            st.session_state.run_override_calc = True

    if st.session_state.run_override_calc:
        payload_rows = st.session_state[grid_key].to_dict(orient="records")

        try:
            result = _post_api_json(
                "/api/v1/reports/calculate",
                {
                    "account_id": account,
                    "sc_code": sc_code,
                    "rows": payload_rows,
                },
            )
        except requests.RequestException as exc:
            st.error(f"Unable to calculate expected bill from API: {exc}")
            return

        result_rows = result.get("rows", [])
        result_df = _result_to_display_df(result_rows)

        st.dataframe(result_df, use_container_width=True)

        m1, m2, m3 = st.columns(3)
        m1.metric("Total Actual", f"${result.get('total_actual', 0.0):,.2f}")
        m2.metric("Total Expected", f"${result.get('total_expected', 0.0):,.2f}")
        m3.metric("Total Variance", f"${result.get('total_variance', 0.0):,.2f}")

        st.download_button(
            "Download Expected Bill (Excel)",
            data=_df_to_excel_bytes(result_df, f"{sc_code}_Overrides"),
            file_name=f"expected_bill_{account}_{sc_code}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


if __name__ == "__main__":
    render_report_viewer()