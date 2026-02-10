import pandas as pd
import streamlit as st
from io import BytesIO
import re

# =========================================================
# HELPERS
# =========================================================

def _clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize column names to snake_case lowercase.
    """
    df = df.copy()
    df.columns = [
        re.sub(r"[^a-z0-9_]+", "_", str(c).lower()).strip("_")
        for c in df.columns
    ]
    return df


def _normalize_expected_bill_schema(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize Expected Bill exports to raw-bill-equivalent schema.
    This prevents downstream column mismatch errors.
    """
    df = df.copy()

    rename_map = {
        "kwh": "billed_kwh",
        "demand_kw": "billed_demand",
        "expected_bill": "bill_amount",
    }

    # Rename only if present
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    return df


def _require_columns(df, required):
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def _prepare_monthly(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepare month-aligned data using pre-calculated bill values.
    """
    df = df.copy()
    df["month"] = pd.to_datetime(df["bill_date"]).dt.strftime("%m-%d-%y")

    return df[
        [
            "month",
            "billed_demand",
            "billed_kwh",
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

def render_savings():
    st.header("Service Classification Savings Analysis")

    st.caption(
        "Upload two Excel files for the same account. "
        "Files may be raw bills or Expected Bill exports."
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
            "Upload New Rate Excel",
            type=["xlsx"],
            key="new_rate",
        )

    if not old_file or not new_file:
        st.info("Upload both files to continue.")
        return

    try:
        # -------------------------------------------------
        # LOAD + NORMALIZE FILES
        # -------------------------------------------------
        old_df = _normalize_expected_bill_schema(
            _clean_columns(pd.read_excel(old_file))
        )
        new_df = _normalize_expected_bill_schema(
            _clean_columns(pd.read_excel(new_file))
        )

        required_cols = [
            "bill_date",
            "billed_kwh",
            "billed_demand",
            "bill_amount",
        ]

        _require_columns(old_df, required_cols)
        _require_columns(new_df, required_cols)

        # -------------------------------------------------
        # MONTHLY ALIGNMENT
        # -------------------------------------------------
        old_monthly = _prepare_monthly(old_df)
        new_monthly = _prepare_monthly(new_df)

        merged = old_monthly.merge(
            new_monthly,
            on="month",
            suffixes=("_old", "_new"),
            how="inner",
        )

        merged["monthly_savings"] = (
            merged["bill_amount_old"]
            - merged["bill_amount_new"]
        )

        # -------------------------------------------------
        # FINAL OUTPUT
        # -------------------------------------------------
        final = pd.DataFrame({
            "Month": merged["month"],
            "Old Demand": merged["billed_demand_old"],
            "New Demand": merged["billed_demand_new"],
            "KWH": merged["billed_kwh_old"],
            "Old Rate Bill": merged["bill_amount_old"].round(2),
            "New Rate Bill": merged["bill_amount_new"].round(2),
            "Monthly Savings": merged["monthly_savings"].round(2),
        })

        st.subheader("Monthly Savings")
        st.dataframe(final, use_container_width=True)

        c1, c2, c3 = st.columns(3)
        c1.metric("Old Total", f"${final['Old Rate Bill'].sum():,.2f}")
        c2.metric("New Total", f"${final['New Rate Bill'].sum():,.2f}")
        c3.metric("12-Month Savings", f"${final['Monthly Savings'].sum():,.2f}")

        st.download_button(
            "Download Savings Spreadsheet",
            data=_to_excel_bytes(final),
            file_name="service_class_savings.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    except Exception as e:
        st.error(str(e))
