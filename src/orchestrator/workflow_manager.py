"""
workflow_manager.py
--------------------
Master orchestrator that coordinates execution of all agents in the Utility Billing AI system.

Purpose:
---------
Controls the end-to-end data flow:
    1) Document ingestion and parsing
    2) Tariff rule extraction
    3) Bill comparison and charge computation
    4) Error detection and validation
    5) Report generation

It manages agent dependencies, error handling, and logging.

Future-ready:
-------------
Can be extended to work with:
    - Apache Airflow DAGs
    - Redis task queues
    - REST API triggers

Usage Example:
--------------
python -m src.orchestrator.workflow_manager
"""

import time
from datetime import datetime
from src.utils.logger import get_logger
from src.database.db_utils import (
    insert_raw_bill_document,
    update_document_status,
    insert_processed_data,
    insert_validation_result,
)
from src.utils.helpers import load_csv, save_csv
from src.utils.data_paths import get_file_path
from src.database.utils.airflow_dag_utils import start_pipeline_run, update_pipeline_run

logger = get_logger(__name__)

# ----------------------------------------------------------------------
# 1) Simulated Agent Runners (placeholder functions)
# ----------------------------------------------------------------------

def run_document_processor():
    """
    Placeholder for Document Processor Agent.
    Reads a sample PDF -> extracts data -> saves to raw folder.
    """
    logger.info("start of document_processor")
    logger.info("Running Document Processor Agent...")
    #time.sleep(1)  # simulate time delay

    # Example metadata
    metadata = {
        "file_name": "aiga.pdf",
        "file_type": "PDF",
        "upload_date": str(datetime.now().date()),
        "source": "City of Hampton",
        "status": "processed"
    }
    insert_raw_bill_document(metadata)
    logger.info("after calling of insert_raw_bill_document(metadata)")
    logger.info("Document Processor completed.")
    logger.info("end of document_processor")
    return True


def run_tariff_analysis():
    """
    Placeholder for Tariff Analysis Agent.
    Extracts rate rules and stores tariff table.
    """
    logger.info("start of run_tariff_analysis")
    logger.info("Running Tariff Analysis Agent...")

    #time.sleep(1)
    logger.info("Tariff Analysis completed.")
    logger.info("end of run_tariff_analysis")
    return True


def run_bill_comparison():
    """
    Placeholder for Bill Comparison Agent.
    Compares actual bills vs tariff-based charges.
    """
    logger.info("start of run_bill_comparison")
    logger.info("Running Bill Comparison Agent...")

    #time.sleep(1)

    # Simulate a small processed DataFrame
    import pandas as pd
    df = pd.DataFrame({
        "account_id": ["sd", "ss"],
        "usage_kwh": [900, 880],
        "actual_charge": [120.0, 118.0],
        "expected_charge": [110.0, 115.0],
        "difference": [10.0, 3.0]
    })

    save_csv(df, "processed", "comparison_results.csv")
    insert_processed_data(df)
    logger.info("after calling of insert_processed_data(df)")
    logger.info("Bill Comparison completed.")
    logger.info("end of run_bill_comparison")
    return True


def run_error_detection():
    """
    Placeholder for Error Detection Agent.
    Identifies anomalies and inserts validation results.
    """
    logger.info("start of run_error_detection")
    logger.info("Running Error Detection Agent...")
    #time.sleep(1)

    record = {
        "account_id": "dagtest",
        "issue_type": "Overcharge",
        "description": "Charge exceeds tariff by $10",
        "detected_on": str(datetime.now().date()),
        "status": "flagged"
    }
    insert_validation_result(record)
    logger.info("after calling of insert_validation_result(record)")
    logger.info("Error Detection completed.")
    logger.info("end of run_error_detection")
    return True


def run_reporting():
    """
    Placeholder for Reporting Agent.
    Generates summary report and saves output.
    """
    logger.info("start of run_reporting")
    logger.info("Running Reporting Agent...")
    #time.sleep(1)
    report_path = get_file_path("output", "Error_Summary_2025_Q4.xlsx")
    logger.info(f"Report generated successfully -> {report_path}")
    logger.info("end of run_reporting")
    return True

# ----------------------------------------------------------------------
# 2) Main Orchestration Function
# ----------------------------------------------------------------------

def run_full_workflow():
    """
    Executes all agents sequentially and logs a pipeline_run entry.
    """
    
    logger.info("Starting full Utility Billing AI workflow...")
    run_id = start_pipeline_run("utility_billing_pipeline")

    try:
        if not run_document_processor():
            raise Exception("Document Processor failed")
        if not run_tariff_analysis():
            raise Exception("Tariff Analysis failed")
        if not run_bill_comparison():
            raise Exception("Bill Comparison failed")
        if not run_error_detection():
            raise Exception("Error Detection failed")
        if not run_reporting():
            raise Exception("Reporting failed")

        update_pipeline_run(run_id, "success")
        logger.info(f"Workflow completed successfully (Run ID {run_id})")
        logger.info("dagtest")
        return True

    except Exception as e:
        update_pipeline_run(run_id, "failed", str(e))
        logger.error(f"Workflow failed (Run ID {run_id}): {e}")
        return False

# ----------------------------------------------------------------------
# 3) Entry Point
# ----------------------------------------------------------------------
if __name__ == "__main__":
    run_full_workflow()
