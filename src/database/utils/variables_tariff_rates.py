"""
variables_tariff_rates.py
-------------------------
Variable tariff rate insert/update utilities for SBC, TRA, RDM, and RAM.
Month-year based UPSERT logic using effective_date normalized to first day of month.
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


def _normalize_to_month_start(eff):
    """
    Convert input date/string to first day of that month.
    Example:
        2021-07-15 -> 2021-07-01
    """
    if eff is None:
        return None

    if isinstance(eff, str):
        eff = dateparser.parse(eff).date()

    return eff.replace(day=1)


def _upsert_rate(model, record: dict):
    session = get_session()
    try:
        eff = _normalize_to_month_start(record.get("effective_date"))
        sc_code = str(record.get("sc_code")).strip() if record.get("sc_code") is not None else None
        rate = record.get("rate")

        if eff is None or not sc_code or rate is None:
            logger.warning(
                f"Skipping upsert for {model.__tablename__}: "
                f"effective_date={eff}, sc_code={sc_code}, rate={rate}"
            )
            return None

        # newest matching month row first
        candidates = (
            session.query(model)
            .filter(model.sc_code == sc_code)
            .order_by(model.effective_date.desc(), model.id.desc())
            .all()
        )

        existing = None
        for row in candidates:
            if row.effective_date.year == eff.year and row.effective_date.month == eff.month:
                existing = row
                break

        if existing:
            existing.rate = rate
            existing.effective_date = eff
            session.flush()
            session.commit()
            session.refresh(existing)
            logger.info(
                f"Updated {model.__tablename__} id={existing.id} "
                f"sc={sc_code} month={eff.strftime('%Y-%m')} rate={rate}"
            )
            return existing.id

        row = model(
            effective_date=eff,
            sc_code=sc_code,
            rate=rate,
        )
        session.add(row)
        session.flush()
        session.commit()
        session.refresh(row)

        logger.info(
            f"Inserted {model.__tablename__} id={row.id} "
            f"sc={sc_code} month={eff.strftime('%Y-%m')} rate={rate}"
        )
        return row.id

    except SQLAlchemyError as e:
        logger.error(f"Failed to upsert rate in {model.__tablename__}: {e}")
        session.rollback()
        return None
    finally:
        session.close()


def insert_sbc_rate(record: dict):
    return _upsert_rate(SBCSystemBenefitsCharge, record)


def insert_tra_rate(record: dict):
    return _upsert_rate(TRATransmissionRevenueAdjustment, record)


def insert_rdm_rate(record: dict):
    return _upsert_rate(RDMRevenueDecouplingMechanism, record)


def insert_ram_rate(record: dict):
    return _upsert_rate(RAMRateAdjustmentMechanism, record)


def fetch_rates_for_dates(table_name: str, sc_code: str, effective_dates: list):
    logger.info("start fetch_rates_for_dates")

    model_map = {
        "sbc": SBCSystemBenefitsCharge,
        "tra": TRATransmissionRevenueAdjustment,
        "rdm": RDMRevenueDecouplingMechanism,
        "ram": RAMRateAdjustmentMechanism,
    }

    model = model_map.get((table_name or "").lower())
    if not model or not effective_dates:
        return []

    normalized_dates = []
    for d in effective_dates:
        parsed = dateparser.parse(d).date() if isinstance(d, str) else d
        normalized_dates.append(parsed)

    session = get_session()
    try:
        # newest rows first
        rows = (
            session.query(model)
            .filter(model.sc_code == sc_code)
            .order_by(model.effective_date.desc(), model.id.desc())
            .all()
        )

        # keep only latest row per (year, month)
        latest_by_month = {}
        for row in rows:
            key = (row.effective_date.year, row.effective_date.month)
            if key not in latest_by_month:
                latest_by_month[key] = row.rate

        results = []
        for original_input, lookup_date in zip(effective_dates, normalized_dates):
            key = (lookup_date.year, lookup_date.month)
            rate = latest_by_month.get(key)

            results.append({
                "effective_date": (
                    original_input
                    if isinstance(original_input, str)
                    else original_input.strftime("%Y-%m-%d")
                ),
                "rate": float(rate) if rate is not None else None,
            })

        return results

    except SQLAlchemyError as e:
        logger.error(f"Failed to fetch rates for {table_name}: {e}")
        return []

    finally:
        session.close()
        logger.info("end fetch_rates_for_dates")