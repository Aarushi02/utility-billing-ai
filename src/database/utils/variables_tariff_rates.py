"""
variables_tariff_rates.py
-------------------------
Variable tariff rate insert/update utilities for SBC, TRA, RDM, and RAM.
Implements UPSERT logic to avoid duplicate rows.
"""

from dateutil import parser as dateparser
from sqlalchemy.exc import SQLAlchemyError

from src.database.db_utils import get_session, logger
from src.database.models import (
    SBCSystemBenefitsCharge,
    TRATransmissionRevenueAdjustment,
    RDMRevenueDecouplingMechanism,
    RAMRateAdjustmentMechanism,
)


def _normalize_date(eff):
    """Convert string date to date object."""
    if isinstance(eff, str):
        return dateparser.parse(eff).date()
    return eff


def _upsert_rate(model, record: dict):
    """
    Generic UPSERT logic for tariff tables.
    """
    session = get_session()
    try:
        eff = _normalize_date(record.get("effective_date"))
        sc_code = record.get("sc_code")
        rate = record.get("rate")

        # check existing row
        existing = (
            session.query(model)
            .filter(model.effective_date == eff)
            .filter(model.sc_code == sc_code)
            .first()
        )

        if existing:
            logger.info(
                f"Updating {model.__tablename__} sc={sc_code} eff={eff}"
            )
            existing.rate = rate
            session.commit()
            return existing.id

        # insert new row
        row = model(
            effective_date=eff,
            sc_code=sc_code,
            rate=rate,
        )

        session.add(row)
        session.commit()

        logger.info(
            f"Inserted {model.__tablename__} id={row.id} sc={sc_code} eff={eff}"
        )
        return row.id

    except SQLAlchemyError as e:
        logger.error(f"Failed to upsert rate in {model.__tablename__}: {e}")
        session.rollback()
        return None
    finally:
        session.close()


def insert_sbc_rate(record: dict):
    """Insert or update SBC rate."""
    logger.info("start insert_sbc_rate")
    result = _upsert_rate(SBCSystemBenefitsCharge, record)
    logger.info("end insert_sbc_rate")
    return result


def insert_tra_rate(record: dict):
    """Insert or update TRA rate."""
    logger.info("start insert_tra_rate")
    result = _upsert_rate(TRATransmissionRevenueAdjustment, record)
    logger.info("end insert_tra_rate")
    return result


def insert_rdm_rate(record: dict):
    """Insert or update RDM rate."""
    logger.info("start insert_rdm_rate")
    result = _upsert_rate(RDMRevenueDecouplingMechanism, record)
    logger.info("end insert_rdm_rate")
    return result


def insert_ram_rate(record: dict):
    """Insert or update RAM rate."""
    logger.info("start insert_ram_rate")
    result = _upsert_rate(RAMRateAdjustmentMechanism, record)
    logger.info("end insert_ram_rate")
    return result


def fetch_rates_for_dates(table_name: str, sc_code: str, effective_dates: list):
    """
    Fetch rates for given service class and effective dates.
    """

    logger.info("start fetch_rates_for_dates")

    model_map = {
        "sbc": SBCSystemBenefitsCharge,
        "tra": TRATransmissionRevenueAdjustment,
        "rdm": RDMRevenueDecouplingMechanism,
        "ram": RAMRateAdjustmentMechanism,
    }

    model = model_map.get((table_name or "").lower())
    if not model:
        logger.warning(f"Unknown table_name={table_name}")
        return []

    if not effective_dates:
        return []

    normalized_dates = [_normalize_date(d) for d in effective_dates]
    date_set = set(normalized_dates)

    session = get_session()

    try:
        rows = (
            session.query(model)
            .filter(model.sc_code == sc_code)
            .order_by(model.effective_date)
            .all()
        )

        row_map = {}

        for bill_date in normalized_dates:
            applicable = None

            for r in rows:
                if r.effective_date <= bill_date:
                    applicable = r.rate
                else:
                    break

            if applicable is not None:
                row_map[bill_date] = applicable

        results = [
            {
                "effective_date": d.strftime("%Y-%m-%d"),
                "rate": row_map[d]
            }
            for d in normalized_dates
            if d in row_map
        ]

        return results

    except SQLAlchemyError as e:
        logger.error(f"Failed to fetch rates for {table_name}: {e}")
        return []

    finally:
        session.close()
        logger.info("end fetch_rates_for_dates")