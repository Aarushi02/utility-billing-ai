"""
db_utils.py
------------
Common database utility functions for interacting with the Utility Billing AI database.

Purpose:
--------
Provides reusable CRUD (Create, Read, Update, Delete) operations for agents.
Helps store extracted data, processed results, and error detections.

Dependencies:
-------------
- SQLAlchemy ORM
- src.utils.config (for DB_URL)
- src.database.models (ORM classes)
"""
from dateutil import parser as dateparser
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
from typing import Union, Optional
from src.utils.config import DB_URL
from src.utils.logger import get_logger
from src.database.models import (
    RawBillDocument,
    LogEntry,
)


logger = get_logger(__name__)

# ----------------------------------------------------------------------
# 1) Setup engine and session factory (lazy-loaded)
# ----------------------------------------------------------------------
_engine = None
_SessionLocal = None

def get_engine():
    """Lazily create and return the SQLAlchemy engine."""
    global _engine
    if _engine is None:
        _engine = create_engine(DB_URL)
    return _engine

def get_session():
    """Lazily create and return a new database session."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine())
    return _SessionLocal()


# ----------------------------------------------------------------------
# 2a) Insert log entry
# ----------------------------------------------------------------------
def insert_log_entry(level: str, description: str, message: str, logger_name: str = None, context: dict = None):
    """Insert a log record into the database.

    This function intentionally avoids logger usage to prevent recursive logging
    when called from logging handlers.
    
    Args:
        level: Log level (INFO, WARNING, ERROR, etc.)
        description: Raw log message (e.g., "start of fetch_user_bills")
        message: Formatted log message with timestamp and logger name
        logger_name: Name of the logger
        context: Additional context (module, filename, line number, etc.)
    """
    session = get_session()
    try:
        entry = LogEntry(
            level=level,
            description=description,
            message=message,
            logger_name=logger_name,
            context=context,
        )
        session.add(entry)
        session.commit()
    except SQLAlchemyError:
        session.rollback()
    finally:
        session.close()

# ----------------------------------------------------------------------
# 2) Insert functions
# ----------------------------------------------------------------------
def insert_raw_bill_document(metadata: dict):
    """
    Inserts a new raw document record (e.g., uploaded file metadata).

    Parameters
    ----------
    metadata : dict
        Should contain file_name, file_type, upload_date, source, status
    """
    logger.info("start of insert_raw_bill_document")
    session = get_session()
    logger.info("session created for insert_raw_bill_document") 
    try:
        doc = RawBillDocument(**metadata)
        logger.info(f"RawBillDocument instance created: {doc}")
        
        session.add(doc)
        session.commit()
        logger.info(f"Inserted raw document: {metadata.get('file_name')} (id={doc.id})")
        return doc.id
    except SQLAlchemyError as e:
        logger.error(f"Failed to insert raw document: {e}")
        session.rollback()
        return None
    finally:
        logger.info("end of insert_raw_bill_document")
        session.close()


# ----------------------------------------------------------------------
# 3) Fetch functions
# ----------------------------------------------------------------------
def fetch_all_raw_bill_docs():
    """Returns a list of all raw documents."""
    logger.info("start of fetch_all_raw_bill_docs")
    session = get_session()
    try:
        results = session.query(RawBillDocument).all()
        logger.info(f"Retrieved {len(results)} raw documents.")
        return results
    except SQLAlchemyError as e:
        logger.error(f"Failed to fetch raw docs: {e}")
        return []
    finally:
        logger.info("end of fetch_all_raw_bill_docs")
        session.close()


# ----------------------------------------------------------------------
# 4) Update functions
# ----------------------------------------------------------------------
def update_document_status(file_name: str, new_status: str):
    """
    Updates the status of a document record (e.g., 'processed', 'error', etc.)
    """
    session = get_session()
    try:
        doc = session.query(RawBillDocument).filter_by(file_name=file_name).first()
        if doc:
            doc.status = new_status
            session.commit()
            logger.info(f"Updated status for {file_name} -> {new_status}")
        else:
            logger.warning(f"Document {file_name} not found in DB.")
    except SQLAlchemyError as e:
        logger.error(f"Failed to update status for {file_name}: {e}")
        session.rollback()
    finally:
        session.close()


