"""
Extract user-entered override values from a grid and store them in DB.
Blank values are ignored completely.
"""

from typing import Callable
import pandas as pd

from src.utils.logger import get_logger

from src.database.utils.variables_tariff_rates import (
    insert_sbc_rate,
    insert_tra_rate,
    insert_rdm_rate,
    insert_ram_rate,
)

logger = get_logger("OverrideValueExtractor")


# =========================================================
# GENERIC EXTRACT + STORE
# =========================================================

def _extract_and_store(
    grid_df: pd.DataFrame,
    *,
    bill_date_col: str,
    rate_column: str,
    insert_fn: Callable[[dict], int | None],
    sc_code_col: str = "service_class",
) -> int:
    """
    Extract a single override column and store values in DB.

    Rules:
    - Blank / NaN → ignored
    - Value present → stored as-is
    """

    if rate_column not in grid_df.columns:
        logger.info(f"Column '{rate_column}' not present. Skipping.")
        return 0

    inserted = 0

    for _, row in grid_df.iterrows():
        rate = row.get(rate_column)

        # IMPORTANT: only store explicitly entered values
        if rate is None or pd.isna(rate):
            continue

        record = {
            "effective_date": row[bill_date_col],
            "sc_code": row[sc_code_col],
            "rate": float(rate),
        }

        try:
            row_id = insert_fn(record)
            if row_id:
                inserted += 1
        except Exception as e:
            logger.error(
                f"Insert failed for {rate_column} "
                f"sc={record['sc_code']} "
                f"eff={record['effective_date']}: {e}"
            )

    logger.info(f"Stored {inserted} rows for '{rate_column}'")
    return inserted


# =========================================================
# PUBLIC ENTRY POINT
# =========================================================

def store_override_values(
    grid_df: pd.DataFrame,
    *,
    bill_date_col: str,
) -> dict:
    """
    Extract and store all supported override columns found in the grid.
    """

    results = {
        "TRA": _extract_and_store(
            grid_df,
            bill_date_col=bill_date_col,
            rate_column="override_tra",
            insert_fn=insert_tra_rate,
        ),
        "RDM": _extract_and_store(
            grid_df,
            bill_date_col=bill_date_col,
            rate_column="override_rdm",
            insert_fn=insert_rdm_rate,
        ),
        "SBC": _extract_and_store(
            grid_df,
            bill_date_col=bill_date_col,
            rate_column="override_sbc",
            insert_fn=insert_sbc_rate,
        ),
        "RAM": _extract_and_store(
            grid_df,
            bill_date_col=bill_date_col,
            rate_column="override_ram",
            insert_fn=insert_ram_rate,
        ),
    }

    logger.info(f"Override storage summary: {results}")
    return results
