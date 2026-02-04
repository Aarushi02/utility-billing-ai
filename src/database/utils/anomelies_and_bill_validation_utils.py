"""
anomelies_and_bill_validation_utils.py
---------------------------------------
Bill validation and anomaly detection result management utilities.

This module centralizes bill validation result operations to keep db_utils focused on
general database operations while preserving existing behavior.
"""

from sqlalchemy.exc import SQLAlchemyError

from src.database.db_utils import get_session, logger
from src.database.models import BillValidationResult


def insert_bill_validation_result(record: dict):
    """
    Inserts a single BillValidationResult record (error, anomaly, or validation finding).
    """
    logger.info("start of insert_bill_validation_result")
    session = get_session()
    try:
        val = BillValidationResult(**record)
        session.add(val)
        session.commit()
        logger.info(
            f"[OK] Bill validation result added "
            f"Account={record.get('account_id')} | Issue={record.get('issue_type')}"
        )
    except SQLAlchemyError as e:
        logger.error(f"[ERROR] Failed to insert bill validation result: {e}")
        session.rollback()
    finally:
        logger.info("end of insert_bill_validation_result")
        session.close()


def fetch_bill_validation_results(
    account_id: str = None,
    user_bill_id: int = None,
    status: str = None,
    limit: int = 100
):
    """
    Fetch BillValidationResult rows optionally filtered by:
    - account_id
    - user_bill_id
    - status ('open', 'resolved', etc.)
    """
    logger.info("start of fetch_bill_validation_results")
    session = get_session()
    try:
        query = session.query(BillValidationResult)

        if account_id:
            query = query.filter_by(account_id=account_id)

        if user_bill_id:
            query = query.filter_by(user_bill_id=user_bill_id)

        if status:
            query = query.filter_by(status=status)

        results = query.order_by(BillValidationResult.detected_on.desc()).limit(limit).all()

        logger.info(f"Retrieved {len(results)} bill validation results.")
        return results

    except SQLAlchemyError as e:
        logger.error(f"Failed to fetch bill validation results: {e}")
        return []
    finally:
        logger.info("end of fetch_bill_validation_results")
        session.close()


def update_bill_validation_result(result_id: int, updates: dict):
    """
    Updates fields of a BillValidationResult row.
    Example: update_bill_validation_result(1, {"status": "resolved"})
    """
    logger.info("start of update_bill_validation_result")
    session = get_session()
    try:
        result = session.query(BillValidationResult).filter_by(id=result_id).first()

        if result:
            for key, value in updates.items():
                setattr(result, key, value)

            session.commit()
            logger.info(f"Updated BillValidationResult id={result_id}")
        else:
            logger.warning(f"BillValidationResult id={result_id} not found.")

    except SQLAlchemyError as e:
        logger.error(f"Failed to update BillValidationResult {result_id}: {e}")
        session.rollback()
    finally:
        logger.info("end of update_bill_validation_result")
        session.close()

