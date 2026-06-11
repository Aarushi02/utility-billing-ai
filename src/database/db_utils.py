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
import re
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
def insert_log_entry(
    level: str,
    message: str,
    description: str | None = None,
    logger_name: str | None = None,
    source: str | None = None,
    log_file: str | None = None,
    context: dict | None = None,
):
    """Insert a log record into the logs table.

    This function intentionally avoids logger usage to prevent recursive logging
    when called from logging handlers.

    Args:
        level: Log level (INFO, WARNING, ERROR, etc.)
        message: Formatted log message
        description: Optional short description/raw message
        logger_name: Name of the logger
        source: Service source (api, streamlit, airflow, utility_billing)
        log_file: Path to originating log file if applicable
        context: Additional context (module, filename, line number, etc.)
    """
    session = get_session()
    try:
        entry = LogEntry(
            level=level,
            message=message,
            description=description,
            logger_name=logger_name,
            source=source,
            log_file=log_file,
            context=context,
        )
        session.add(entry)
        session.commit()
    except SQLAlchemyError:
        session.rollback()
    finally:
        session.close()


def import_log_file(file_path: str, source: str, max_lines: int = 5000) -> int:
    """Import plain-text log lines into the logs table.

    Supports both structured logger lines and generic text lines.
    Returns number of inserted rows.
    """
    line_pattern = re.compile(
        r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s*\|\s*(?P<level>[A-Z]+)\s*\|\s*(?P<logger>[^|]+)\|\s*(?P<msg>.*)$"
    )

    inserted = 0
    session = get_session()
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            for i, raw_line in enumerate(f):
                if i >= max_lines:
                    break
                line = raw_line.rstrip("\n")
                if not line.strip():
                    continue

                level = "INFO"
                logger_name = None
                message = line
                description = None

                match = line_pattern.match(line)
                if match:
                    level = match.group("level")
                    logger_name = match.group("logger").strip()
                    description = match.group("msg").strip()
                    message = line

                entry = LogEntry(
                    source=source,
                    level=level,
                    message=message,
                    description=description,
                    logger_name=logger_name,
                    log_file=file_path,
                    context={"imported": True, "line_number": i + 1},
                )
                session.add(entry)
                inserted += 1

        session.commit()
        return inserted
    except Exception:
        session.rollback()
        return 0
    finally:
        session.close()

# ----------------------------------------------------------------------
# 2) Insert functions
# ----------------------------------------------------------------------
def insert_raw_bill_document(metadata: dict):
    """
    Inserts a new raw document record (e.g., uploaded file metadata).

    If a document with the same file_name already exists,
    an error is logged and insertion is skipped.

    Parameters
    ----------
    metadata : dict
        Should contain file_name, file_type, upload_date, source, status
    """
    logger.info("start of insert_raw_bill_document")
    session = get_session()
    logger.info("session created for insert_raw_bill_document")

    try:
        file_name = metadata.get("file_name")

        if not file_name:
            logger.error("File name is required in metadata.")
            raise ValueError("File name is required.")

        # ----------------------------------------------------
        # Step 1: Check if exact same bill already exists
        # ----------------------------------------------------
        existing_doc = (
            session.query(RawBillDocument)
            .filter(RawBillDocument.file_name == file_name)
            .first()
        )

        if existing_doc:
            error_msg = f"Duplicate bill detected: '{file_name}' already exists (id={existing_doc.id})"
            logger.error(error_msg)
            return existing_doc.id

        # ----------------------------------------------------
        # Step 2: Insert new document if no duplicate found
        # ----------------------------------------------------
        doc = RawBillDocument(**metadata)
        session.add(doc)
        session.commit()

        logger.info(f"Inserted raw document: {file_name} (id={doc.id})")
        return doc.id

    except (SQLAlchemyError, ValueError) as e:
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


