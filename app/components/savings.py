import pandas as pd
import streamlit as st
from io import BytesIO
import re

# =========================================================
# HELPERS
# =========================================================

def _clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [
        re.sub(r"[^a-z0-9_]+", "_", str(c).lower()).strip("_")
        for c in df.columns
    ]
    return df


def _require_columns(df, required):
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def _prepare_monthly(df: pd.DataFrame) -> pd.DataFrame:
    """
    Uses PRE-CALCULATED bill_amount from Excel.
    No recomputation.
    """
    df = df.copy()
    df["month"] = pd.to_datetime(df["bill_date"]).dt.strftime("%m-%d-%y")

    return df[
        [
            "month",
            "billed_demand",
            "billed_kwh",
            "tra",
            "rdm",
            "bill_amount",
        ]
    ]


def _to_excel_bytes(df: pd.DataFrame, sheet_name="Savings"):
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    buf.seek(0)
    return buf


# =========================================================
# SAVINGS COMPONENT
# =========================================================

def savings():
    st.header("Service Classification Savings Analysis")

    st.caption(
        "Upload two Excel files for the same account "
        "Bills must already be calculated."
    )

    col1, col2 = st.columns(2)

    with col1:
        old_file = st.file_uploader(
            "Upload Old Rate Excel",
            type=["xlsx"],
            key="old_rate",
        )

    with col2:
        new_file = st.file_uploader(
            "Upload New RateExcel",
            type=["xlsx"],
            key="new_rate",
        )

    if not old_file or not new_file:
        st.info("Upload both files to continue.")
        return

    try:
        old_df = _clean_columns(pd.read_excel(old_file))
        new_df = _clean_columns(pd.read_excel(new_file))

        required_cols = [
            "bill_date",
            "kwh",
            "demand_kw",
            "expected_bill",   # <-- already calculated
        ]

        _require_columns(old_df, required_cols)
        _require_columns(new_df, required_cols)

        old_monthly = _prepare_monthly(old_df)
        new_monthly = _prepare_monthly(new_df)

        # =================================================
        # ALIGN MONTHS
        # =================================================

        merged = old_monthly.merge(
            new_monthly,
            on="month",
            suffixes=("_sc3", "_sc2d"),
            how="inner",
        )

        merged["monthly_savings"] = (
            merged["expected_sc3"]
            - merged["expected_bill_sc2d"]
        )

        # =================================================
        # FINAL OUTPUT (MATCHES IMAGE)
        # =================================================

        final = pd.DataFrame({
            "Month": merged["month"],
            "SC3 Demand": merged["demand_kw_sc3"],
            "SC2D Demand": merged["demand_kw_sc2d"],
            "KWH": merged["kwh_sc3"],
            "TRA-SC3": merged["tra_sc3"],
            "RDM-SC3": merged["rdm_sc3"],
            "TRA-SC2D": merged["tra_sc2d"],
            "RDM-SC2D": merged["rdm_sc2d"],
            "SC3 (Old Rate)": merged["expected_bill_sc3"].round(2),
            "SC2D (New Rate)": merged["expected_bill_sc2d"].round(2),
            "Monthly Savings": merged["monthly_savings"].round(2),
        })

        st.subheader("Monthly Savings")
        st.dataframe(final, use_container_width=True)

        total_old = final["SC3 (Old Rate)"].sum()
        total_new = final["SC2D (New Rate)"].sum()
        total_savings = final["Monthly Savings"].sum()

        c1, c2, c3 = st.columns(3)
        c1.metric("SC3 Total", f"${total_old:,.2f}")
        c2.metric("SC2D Total", f"${total_new:,.2f}")
        c3.metric("12-Month Savings", f"${total_savings:,.2f}")

        st.download_button(
            "Download Savings Spreadsheet",
            data=_to_excel_bytes(final),
            file_name="service_class_savings.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    except Exception as e:
        st.error(str(e))
