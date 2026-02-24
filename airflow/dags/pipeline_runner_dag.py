"""
tariff_pipeline_runner_dag.py
--------------------------------
Airflow DAG that uses pipeline_runner.run_tariff_pipeline()
to execute the full tariff pipeline as a single task.
"""

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator
from datetime import datetime, timedelta
from pathlib import Path
import sys

# -------------------------------------------------------
# Add project root to Python path
# -------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

# Import pipeline runner
from src.orchestrator.pipeline_runner import run_tariff_pipeline


# -------------------------------------------------------
# Default DAG arguments
# -------------------------------------------------------
default_args = {
    "owner": "troybanks",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}


# -------------------------------------------------------
# Task Wrapper
# -------------------------------------------------------
def run_pipeline_task(**context):
    """
    Wrapper function to call pipeline_runner.run_tariff_pipeline()
    using PDF path passed via DAG conf.
    """

    dag_run = context.get("dag_run")
    conf = dag_run.conf if dag_run else {}

    pdf_path = conf.get("pdf_path")
    raw_bill_document_id = conf.get("raw_bill_document_id")

    if not pdf_path:
        raise ValueError(
            "Missing 'pdf_path' in DAG configuration.\n"
            "Trigger with:\n"
            "airflow dags trigger tariff_pipeline_runner "
            "--conf '{\"pdf_path\": \"data/raw/tariff.pdf\"}'"
        )

    result = run_tariff_pipeline(
        pdf_path=Path(pdf_path),
        raw_bill_document_id=raw_bill_document_id
    )

    print("\nPipeline completed successfully!")
    print(f"Grouped Tariffs: s3://{result['grouped_tariffs']}")
    print(f"Final Logic: s3://{result['final_logic']}")

    return result


# -------------------------------------------------------
# DAG Definition
# -------------------------------------------------------
with DAG(
    dag_id="tariff_pipeline_runner",
    default_args=default_args,
    description="Tariff Pipeline using pipeline_runner module",
    schedule=None,  # Manual trigger only
    start_date=datetime(2025, 12, 1),
    catchup=False,
    tags=["tariff", "pipeline_runner"],
) as dag:

    run_tariff_pipeline_task = PythonOperator(
        task_id="run_tariff_pipeline",
        python_callable=run_pipeline_task,
    )

    run_tariff_pipeline_task