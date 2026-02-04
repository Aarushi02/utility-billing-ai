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
