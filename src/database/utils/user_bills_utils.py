"""
user_bills_utils.py
-------------------
UserBills insert/fetch utilities.
"""

import pandas as pd
from sqlalchemy.exc import SQLAlchemyError

from src.database.db_utils import get_engine, get_session, logger
from src.database.models import BillValidationResult, UserBills


def insert_user_bill(record: dict, raw_bill_document_id: int = None):
	"""
	Inserts a single UserBills record.

	Parameters
	----------
	record : dict
		Bill data dictionary
	raw_bill_document_id : int, optional
		Foreign key reference to raw_documents table

	Returns
	-------
	str or None
		The bill_account that was inserted, or None if insertion failed.
	"""
	logger.info("start of insert_user_bill")
	session = get_session()
	try:
		bill = UserBills(**record)
		if raw_bill_document_id:
			bill.raw_bill_document_id = raw_bill_document_id
		session.add(bill)
		session.commit()
		bill_account = record.get("bill_account")
		logger.info(
			f"Inserted UserBills record for Account {bill_account} (raw_doc_id={raw_bill_document_id})"
		)
		return bill_account
	except SQLAlchemyError as e:
		logger.error(f"Failed to insert UserBills record: {e}")
		session.rollback()
		return None
	finally:
		logger.info("end of insert_user_bill")
		session.close()


def insert_user_bills_bulk(df: pd.DataFrame):
	"""
	Bulk insert UserBills records from a DataFrame.
	"""
	logger.info("start of insert_user_bills_bulk")
	session = get_session()
	try:
		db_cols = [
			"bill_account",
			"customer",
			"bill_date",
			"read_date",
			"days_used",
			"billed_kwh",
			"billed_demand",
			"load_factor",
			"billed_rkva",
			"bill_amount",
			"sales_tax_amt",
			"bill_amount_with_sales_tax",
			"retracted_amt",
			"sales_tax_factor",
		]
		for col in db_cols:
			if col not in df.columns:
				df[col] = None
		df = df[db_cols]
		if "bill_date" in df.columns:
			try:
				df["bill_date"] = pd.to_datetime(df["bill_date"], errors="coerce")
			except Exception:
				pass
		if "read_date" in df.columns:
			try:
				df["read_date"] = pd.to_datetime(df["read_date"], errors="coerce")
			except Exception:
				pass
		df.to_sql("user_bills", get_engine(), if_exists="append", index=False, method="multi")
		logger.info(f"Inserted {len(df)} rows into UserBills table.")
	except Exception as e:
		logger.error(f"Failed to insert UserBills bulk: {e}")
	finally:
		logger.info("end of insert_user_bills_bulk")
		session.close()


def fetch_user_bills(account_id: str | None = None):
	"""
	Fetch all user bills.
	Optionally filter by bill_account.
	"""
	logger.info("start of fetch_user_bills")
	session = get_session()

	try:
		query = session.query(UserBills)

		if account_id:
			# Filter by bill_account with trim
			query = query.filter(UserBills.bill_account == account_id.strip())

		results = query.all()

		# Convert ORM objects to list of dicts for pandas DataFrame
		data = [
			{
				"id": r.id,
				"bill_account": r.bill_account,
				"customer": r.customer,
				"bill_date": r.bill_date,
				"read_date": r.read_date,
				"days_used": r.days_used,
				"billed_kwh": r.billed_kwh,
				"billed_demand": r.billed_demand,
				"load_factor": r.load_factor,
				"billed_rkva": r.billed_rkva,
				"bill_amount": r.bill_amount,
				"sales_tax_amt": r.sales_tax_amt,
				"bill_amount_with_sales_tax": r.bill_amount_with_sales_tax,
				"retracted_amt": r.retracted_amt,
				"sales_tax_factor": r.sales_tax_factor,
				"created_at": r.created_at,
			}
			for r in results
		]

		df = pd.DataFrame(data)
		logger.info(f"Fetched {len(df)} UserBills rows.")
		return df

	except SQLAlchemyError as e:
		logger.error(f"Failed to fetch UserBills: {e}")
		return pd.DataFrame()

	finally:
		logger.info("end of fetch_user_bills")
		session.close()


def fetch_all_account_numbers():
	"""Return a list of all distinct bill_account values from user_bills."""
	logger.info("start of fetch_all_account_numbers")
	session = get_session()

	try:
		# Use ORM to query distinct account numbers
		accounts = session.query(UserBills.bill_account).distinct().all()

		# Extract the account values from the result tuples
		account_list = [account[0] for account in accounts if account[0]]

		logger.info(f"Found {len(account_list)} distinct account numbers.")
		return account_list

	except SQLAlchemyError as e:
		logger.error(f"Failed to fetch account numbers: {e}")
		# Return empty list instead of crashing - tables might not exist yet
		return []

	finally:
		logger.info("end of fetch_all_account_numbers")
		session.close()


def fetch_user_bills_with_issues(account_id: str, issue_type: str | None = None):
	"""
	Fetch ONLY the user bills that have validation issues
	for the given account_id using SQLAlchemy ORM.
	"""
	logger.info("start of fetch_user_bills_with_issues")
	session = get_session()

	try:
		# Query with JOIN between UserBills and BillValidationResult
		query = session.query(
			UserBills.id.label("bill_id"),
			BillValidationResult.user_bill_id.label("fk_user_bill_id"),
			BillValidationResult.id.label("issue_id"),
			UserBills.bill_account,
			UserBills.customer,
			UserBills.bill_date,
			UserBills.read_date,
			UserBills.days_used,
			UserBills.billed_kwh,
			UserBills.billed_demand,
			UserBills.load_factor,
			UserBills.billed_rkva,
			UserBills.bill_amount,
			UserBills.sales_tax_amt,
			UserBills.bill_amount_with_sales_tax,
			UserBills.retracted_amt,
			UserBills.sales_tax_factor,
			UserBills.created_at.label("bill_created_at"),
			BillValidationResult.issue_type,
			BillValidationResult.description,
			BillValidationResult.status,
			BillValidationResult.detected_on,
		).join(
			BillValidationResult,
			UserBills.id == BillValidationResult.user_bill_id,
		).filter(
			UserBills.bill_account == account_id.strip()
		)

		if issue_type:
			query = query.filter(BillValidationResult.issue_type == issue_type)

		results = query.all()

		# Convert to DataFrame
		data = [
			{
				"bill_id": r.bill_id,
				"fk_user_bill_id": r.fk_user_bill_id,
				"issue_id": r.issue_id,
				"bill_account": r.bill_account,
				"customer": r.customer,
				"bill_date": r.bill_date,
				"read_date": r.read_date,
				"days_used": r.days_used,
				"billed_kwh": r.billed_kwh,
				"billed_demand": r.billed_demand,
				"load_factor": r.load_factor,
				"billed_rkva": r.billed_rkva,
				"bill_amount": r.bill_amount,
				"sales_tax_amt": r.sales_tax_amt,
				"bill_amount_with_sales_tax": r.bill_amount_with_sales_tax,
				"retracted_amt": r.retracted_amt,
				"sales_tax_factor": r.sales_tax_factor,
				"bill_created_at": r.bill_created_at,
				"issue_type": r.issue_type,
				"description": r.description,
				"status": r.status,
				"detected_on": r.detected_on,
			}
			for r in results
		]

		df = pd.DataFrame(data)
		logger.info(f"Found {len(df)} bills with issues for account {account_id}.")
		return df

	except SQLAlchemyError as e:
		logger.error(f"Failed to fetch bills with issues: {e}")
		return pd.DataFrame()

	finally:
		logger.info("end of fetch_user_bills_with_issues")
		session.close()
