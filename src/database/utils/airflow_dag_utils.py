"""
airflow_dag_utils.py
--------------------
Pipeline run management utilities for Airflow DAGs.

This module centralizes pipeline run tracking logic to keep db_utils focused on
general database operations while preserving existing behavior.
"""

from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError

from src.database.db_utils import get_session, logger
from src.database.models import PipelineRun


def start_pipeline_run(dag_id: str):
    """
    Creates a new pipeline run entry and returns its run_id.
    """
    logger.info("start of start_pipeline_run")
    session = get_session()
    try:
        run = PipelineRun(dag_id=dag_id, status="running")
        session.add(run)
        session.commit()
        logger.info(f"Started pipeline run {run.id} for {dag_id}")
        return run.id
    except SQLAlchemyError as e:
        logger.error(f"Failed to start pipeline run: {e}")
        session.rollback()
        return None
    finally:
        logger.info("end of start_pipeline_run")
        session.close()


def update_pipeline_run(run_id: int, status: str, error_msg: str = None):
    """
    Updates pipeline run end_time, total_runtime, and final status.
    """
    logger.info("start of update_pipeline_run")
    session = get_session()
    try:
        run = session.query(PipelineRun).filter_by(id=run_id).first()
        if run:
            run.end_time = datetime.utcnow()
            run.status = status
            if run.start_time:
                run.total_runtime = int((run.end_time - run.start_time).total_seconds())
            run.error_msg = error_msg
            session.commit()
            logger.info(f"Updated pipeline run {run_id} -> {status}")
        else:
            logger.warning(f"Pipeline run {run_id} not found.")
    except SQLAlchemyError as e:
        logger.error(f"Failed to update pipeline run {run_id}: {e}")
        session.rollback()
    finally:
        logger.info("end of update_pipeline_run")
        session.close()
