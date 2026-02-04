"""
variables_tariff_rates.py
-------------------------
Variable tariff rate insert utilities for SBC, TRA, RDM, and RAM.

This module centralizes rate insert logic to keep db_utils focused on
general database operations while preserving existing behavior.
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


def insert_sbc_rate(record: dict):
	"""
	Insert a System Benefits Charge (SBC) rate row.
	Expects keys: effective_date (date or ISO string), sc_code, rate
	Returns the inserted row id or None on failure.
	"""
	logger.info("start of insert_sbc_rate")
	session = get_session()
	try:
		eff = record.get("effective_date")
		if isinstance(eff, str):
			eff = dateparser.parse(eff).date()

		row = SBCSystemBenefitsCharge(
			effective_date=eff,
			sc_code=record.get("sc_code"),
			rate=record.get("rate"),
		)
		session.add(row)
		session.commit()
		logger.info(f"Inserted SBC rate id={row.id} sc={row.sc_code} eff={row.effective_date}")
		return row.id
	except SQLAlchemyError as e:
		logger.error(f"Failed to insert SBC rate: {e}")
		session.rollback()
		return None
	finally:
		logger.info("end of insert_sbc_rate")
		session.close()


def insert_tra_rate(record: dict):
	"""
	Insert a Transmission Revenue Adjustment (TRA) rate row.
	Expects keys: effective_date (date or ISO string), sc_code, rate
	Returns the inserted row id or None on failure.
	"""
	logger.info("start of insert_tra_rate")
	session = get_session()
	try:
		eff = record.get("effective_date")
		if isinstance(eff, str):
			eff = dateparser.parse(eff).date()

		row = TRATransmissionRevenueAdjustment(
			effective_date=eff,
			sc_code=record.get("sc_code"),
			rate=record.get("rate"),
		)
		session.add(row)
		session.commit()
		logger.info(f"Inserted TRA rate id={row.id} sc={row.sc_code} eff={row.effective_date}")
		return row.id
	except SQLAlchemyError as e:
		logger.error(f"Failed to insert TRA rate: {e}")
		session.rollback()
		return None
	finally:
		logger.info("end of insert_tra_rate")
		session.close()


def insert_rdm_rate(record: dict):
	"""
	Insert a Revenue Decoupling Mechanism (RDM) rate row.
	Expects keys: effective_date (date or ISO string), sc_code, rate
	Returns the inserted row id or None on failure.
	"""
	logger.info("start of insert_rdm_rate")
	session = get_session()
	try:
		eff = record.get("effective_date")
		if isinstance(eff, str):
			eff = dateparser.parse(eff).date()

		row = RDMRevenueDecouplingMechanism(
			effective_date=eff,
			sc_code=record.get("sc_code"),
			rate=record.get("rate"),
		)
		session.add(row)
		session.commit()
		logger.info(f"Inserted RDM rate id={row.id} sc={row.sc_code} eff={row.effective_date}")
		return row.id
	except SQLAlchemyError as e:
		logger.error(f"Failed to insert RDM rate: {e}")
		session.rollback()
		return None
	finally:
		logger.info("end of insert_rdm_rate")
		session.close()


def insert_ram_rate(record: dict):
	"""
	Insert a Rate Adjustment Mechanism (RAM) rate row.
	Expects keys: effective_date (date or ISO string), sc_code, rate
	Returns the inserted row id or None on failure.
	"""
	logger.info("start of insert_ram_rate")
	session = get_session()
	try:
		eff = record.get("effective_date")
		if isinstance(eff, str):
			eff = dateparser.parse(eff).date()

		row = RAMRateAdjustmentMechanism(
			effective_date=eff,
			sc_code=record.get("sc_code"),
			rate=record.get("rate"),
		)
		session.add(row)
		session.commit()
		logger.info(f"Inserted RAM rate id={row.id} sc={row.sc_code} eff={row.effective_date}")
		return row.id
	except SQLAlchemyError as e:
		logger.error(f"Failed to insert RAM rate: {e}")
		session.rollback()
		return None
	finally:
		logger.info("end of insert_ram_rate")
		session.close()


def fetch_rates_for_dates(table_name: str, sc_code: str, effective_dates: list):
	"""
	Fetch rates for a given SC code and a list of effective dates.
	
	Parameters
	----------
	table_name : str
		One of: "sbc", "tra", "rdm", "ram"
	sc_code : str
		Service class code
	effective_dates : list
		List of dates (date objects) or ISO date strings
	
	Returns
	-------
	list of dict
		Each item has: effective_date (YYYY-MM-DD), rate
	"""
	logger.info("start of fetch_rates_for_dates")
	model_map = {
		"sbc": SBCSystemBenefitsCharge,
		"tra": TRATransmissionRevenueAdjustment,
		"rdm": RDMRevenueDecouplingMechanism,
		"ram": RAMRateAdjustmentMechanism,
	}

	model = model_map.get((table_name or "").lower())
	if model is None:
		logger.warning(f"Unknown table_name={table_name}")
		return []

	if not effective_dates:
		return []

	# Normalize dates
	normalized_dates = []
	for d in effective_dates:
		if isinstance(d, str):
			normalized_dates.append(dateparser.parse(d).date())
		else:
			normalized_dates.append(d)

	# Keep a set for filtering
	date_set = set(normalized_dates)

	session = get_session()
	try:
		rows = (
			session.query(model)
			.filter(model.sc_code == sc_code)
			.filter(model.effective_date.in_(date_set))
			.all()
		)
		# Map to dict for quick lookup
		row_map = {
			r.effective_date: r.rate for r in rows
		}
		# Preserve input order, return only available dates
		results = []
		for d in normalized_dates:
			if d in row_map:
				results.append({
					"effective_date": d.strftime("%Y-%m-%d"),
					"rate": row_map[d],
				})
		return results
	except SQLAlchemyError as e:
		logger.error(f"Failed to fetch rates for {table_name}: {e}")
		return []
	finally:
		logger.info("end of fetch_rates_for_dates")
		session.close()
