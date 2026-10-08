import pandas as pd
import streamlit as st
from io import BytesIO
import re

from sqlalchemy import text

from src.database.db_utils import get_engine

# =========================================================
# HELPERS
# =========================================================

NO_DEDUPE = "Don't change (review first)"
KEEP_FIRST = "Keep first row per date"
KEEP_LAST = "Keep last row per date"


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
    Keeps a real date column (bill_date) for joining and for the database.
    """
    df = df.copy()
    df["bill_date"] = pd.to_datetime(df["bill_date"]).dt.normalize()
    df["month"] = df["bill_date"].dt.strftime("%m-%d-%y")

    for col in ["billed_demand", "billed_kwh", "bill_amount"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    return df[
        [
            "bill_date",
            "month",
            "billed_demand",
            "billed_kwh",
            "bill_amount",
        ]
    ]


def _find_duplicate_dates(df: pd.DataFrame) -> pd.DataFrame:
    return df[df.duplicated("bill_date", keep=False)].sort_values("bill_date")


def _resolve_duplicates(df: pd.DataFrame, policy: str) -> pd.DataFrame:
    if policy == KEEP_FIRST:
        return df.drop_duplicates("bill_date", keep="first")
    if policy == KEEP_LAST:
        return df.drop_duplicates("bill_date", keep="last")
    return df


def _parse_file_meta(filename: str) -> tuple[str, str]:
    """
    Pull account and service class out of names like
    expected_bill_1031293107_SC1C.xlsx. Returns ("", "") if no match.
    """
    match = re.search(r"expected_bill_(\d+)_([A-Za-z0-9]+)", filename or "")
    if match:
        return match.group(1), match.group(2).upper()
    return "", ""


def _to_excel_bytes(df: pd.DataFrame, sheet_name="Savings"):
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    buf.seek(0)
    return buf


def _save_savings_to_db(
    merged: pd.DataFrame, account_id: str, old_sc: str, new_sc: str
) -> int:
    """
    Replace all stored rows for (account, old_sc, new_sc) with the current
    analysis. Delete + insert run in one transaction, so re-saving never
    duplicates rows.
    """
    out = pd.DataFrame({
        "bill_date": merged["bill_date"].dt.date,
        "kwh": merged["billed_kwh_old"].round(2),
        "old_demand": merged["billed_demand_old"].round(2),
        "new_demand": merged["billed_demand_new"].round(2),
        "old_bill": merged["bill_amount_old"].round(2),
        "new_bill": merged["bill_amount_new"].round(2),
        "savings": merged["monthly_savings"].round(2),
    })

    records = []
    for row in out.to_dict(orient="records"):
        row = {k: (None if pd.isna(v) else v) for k, v in row.items()}
        row.update(
            account_id=account_id,
            old_sc=old_sc,
            new_sc=new_sc,
            rate_change=f"{old_sc} -> {new_sc}",
        )
        records.append(row)

    with get_engine().begin() as conn:
        conn.execute(
            text(
                """
                DELETE FROM savings_analysis
                WHERE account_id = :account_id
                  AND old_sc = :old_sc
                  AND new_sc = :new_sc
                """
            ),
            {"account_id": account_id, "old_sc": old_sc, "new_sc": new_sc},
        )
        conn.execute(
            text(
                """
                INSERT INTO savings_analysis
                    (account_id, old_sc, new_sc, rate_change, bill_date, kwh,
                     old_demand, new_demand, old_bill, new_bill, savings)
                VALUES
                    (:account_id, :old_sc, :new_sc, :rate_change, :bill_date, :kwh,
                     :old_demand, :new_demand, :old_bill, :new_bill, :savings)
                """
            ),
            records,
        )

    return len(records)


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

        # -------------------------------------------------
        # DUPLICATE DATES (one date appearing on more than one row)
        # A merge on date multiplies rows when either side has duplicates,
        # which double counts the other side's bill.
        # -------------------------------------------------
        old_dups = _find_duplicate_dates(old_monthly)
        new_dups = _find_duplicate_dates(new_monthly)

        policy = NO_DEDUPE
        if not old_dups.empty or not new_dups.empty:
            st.warning(
                f"Duplicate bill dates found: {old_dups['bill_date'].nunique()} "
                f"in the old file, {new_dups['bill_date'].nunique()} in the new file. "
                "Duplicates inflate totals. Check the source files, or choose "
                "how to resolve them below."
            )
            with st.expander("Show duplicate rows"):
                if not old_dups.empty:
                    st.caption("Old file")
                    st.dataframe(old_dups, use_container_width=True)
                if not new_dups.empty:
                    st.caption("New file")
                    st.dataframe(new_dups, use_container_width=True)

            policy = st.selectbox(
                "Resolve duplicate dates",
                [NO_DEDUPE, KEEP_FIRST, KEEP_LAST],
                key="dup_policy",
            )
            old_monthly = _resolve_duplicates(old_monthly, policy)
            new_monthly = _resolve_duplicates(new_monthly, policy)

        unresolved_dups = (
            not _find_duplicate_dates(old_monthly).empty
            or not _find_duplicate_dates(new_monthly).empty
        )

        merged = old_monthly.merge(
            new_monthly,
            on=["bill_date", "month"],
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

        m1, m2, m3 = st.columns(3)
        m1.metric("Old Total", f"${final['Old Rate Bill'].sum():,.2f}")
        m2.metric("New Total", f"${final['New Rate Bill'].sum():,.2f}")
        m3.metric(
            f"Total Savings ({len(final)} bills)",
            f"${final['Monthly Savings'].sum():,.2f}",
        )

        st.download_button(
            "Download Savings Spreadsheet",
            data=_to_excel_bytes(final),
            file_name="service_class_savings.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        # -------------------------------------------------
        # SAVE FOR POWER BI
        # -------------------------------------------------
        st.subheader("Save for Power BI")

        acct_old, sc_old = _parse_file_meta(old_file.name)
        acct_new, sc_new = _parse_file_meta(new_file.name)

        if acct_old and acct_new and acct_old != acct_new:
            st.warning(
                f"The file names show different accounts ({acct_old} vs "
                f"{acct_new}). Make sure both files are for the same account."
            )

        file_tag = f"{old_file.name}|{new_file.name}"
        s1, s2, s3 = st.columns(3)
        account_id = s1.text_input(
            "Account", value=acct_old or acct_new, key=f"sv_acct_{file_tag}"
        ).strip()
        old_sc = s2.text_input(
            "Old service class", value=sc_old, key=f"sv_old_{file_tag}"
        ).strip().upper()
        new_sc = s3.text_input(
            "New service class", value=sc_new, key=f"sv_new_{file_tag}"
        ).strip().upper()

        blockers = []
        if unresolved_dups:
            blockers.append("resolve the duplicate dates above")
        if not (account_id and old_sc and new_sc):
            blockers.append("fill in account and both service classes")
        if merged.empty:
            blockers.append("no matching dates between the two files")

        if blockers:
            st.caption("To save, " + "; ".join(blockers) + ".")

        if st.button("Save to dashboard", disabled=bool(blockers)):
            try:
                count = _save_savings_to_db(merged, account_id, old_sc, new_sc)
                st.success(
                    f"Saved {count} rows for account {account_id} "
                    f"({old_sc} -> {new_sc}). Refresh Power BI to see them."
                )
            except Exception as exc:
                st.error(f"Unable to save to the database: {exc}")

    except Exception as e:
        st.error(str(e))
