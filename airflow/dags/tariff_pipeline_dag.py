"""
tariff_pipeline_dag.py
----------------------
Airflow DAG to orchestrate the Tariff Analysis Pipeline.

This DAG runs the complete tariff processing workflow in separate tasks:
1. Extract text from PDF pages (pagewise_text_extractor.py)
2. Group tariffs by service class (group_extracted_raw_text.py)
3. Extract tariff logic using LLM (extract_logic_llm_call.py)

Triggered manually with a PDF file path parameter.
"""

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator
from datetime import datetime, timedelta
import sys
import subprocess
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

# Default arguments for the DAG
default_args = {
    'owner': 'troybanks',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
}


def extract_text_from_pdf(**context):
    """
    Step 1: Extract text from PDF pages using pagewise_text_extractor.py
    """
    from src.utils.aws_app import file_exists_in_s3, get_s3_key
    
    # Get PDF path from DAG run config
    dag_run = context.get('dag_run')
    conf = dag_run.conf if dag_run else {}
    pdf_path = conf.get('pdf_path')
    
    if not pdf_path:
        raise ValueError("Missing 'pdf_path' in DAG run configuration. "
                        "Trigger with: airflow dags trigger tariff_pipeline "
                        "--conf '{\"pdf_path\": \"data/raw/tariff.pdf\"}'")
    
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    
    print(f"\n🔄 Step 1/3: Extracting text from PDF pages...")
    print(f"📄 PDF Path: {pdf_path}")
    
    step1_script = project_root / "src" / "agents" / "tariff_analysis_agent" / "pagewise_text_extractor.py"
    if not step1_script.exists():
        raise FileNotFoundError(f"Missing: {step1_script}")
    
    subprocess.run([sys.executable, str(step1_script), str(pdf_path)], check=True)
    
    # Validate output in S3
    s3_key_raw = get_s3_key("processed", "raw_extracted_tarif.json")
    if not file_exists_in_s3(s3_key_raw):
        raise RuntimeError(f"raw_extracted_tarif.json was not created in S3: {s3_key_raw}")
    
    print("✅ Step 1/3: Text extraction completed!")
    return {"s3_key": s3_key_raw, "pdf_path": str(pdf_path)}


def group_tariffs_by_service_class(**context):
    """
    Step 2: Group tariffs by service class using group_extracted_raw_text.py
    """
    from src.utils.aws_app import file_exists_in_s3, get_s3_key
    
    print(f"\n🔄 Step 2/3: Grouping tariffs by service class...")
    
    step2_script = project_root / "src" / "agents" / "tariff_analysis_agent" / "group_extracted_raw_text.py"
    if not step2_script.exists():
        raise FileNotFoundError(f"Missing: {step2_script}")
    
    subprocess.run([sys.executable, str(step2_script)], check=True)
    
    # Validate output in S3
    s3_key_grouped = get_s3_key("processed", "grouped_tariffs.json")
    if not file_exists_in_s3(s3_key_grouped):
        raise RuntimeError(f"grouped_tariffs.json was not created in S3: {s3_key_grouped}")
    
    print("✅ Step 2/3: Tariff grouping completed!")
    return {"s3_key": s3_key_grouped}


def extract_logic_using_llm(**context):
    """
    Step 3: Extract tariff logic using LLM via extract_logic_llm_call.py
    """
    from src.utils.aws_app import file_exists_in_s3, get_s3_key
    
    # Get PDF path from upstream task
    ti = context['ti']
    step1_output = ti.xcom_pull(task_ids='extract_text_from_pdf')
    pdf_path = step1_output.get('pdf_path') if step1_output else None
    
    if not pdf_path:
        raise ValueError("Could not retrieve pdf_path from previous task")
    
    print(f"\n🔄 Step 3/3: Extracting tariff logic using LLM...")
    
    step3_script = project_root / "src" / "agents" / "tariff_analysis_agent" / "extract_logic_llm_call.py"
    if not step3_script.exists():
        raise FileNotFoundError(f"Missing: {step3_script}")
    
    subprocess.run([sys.executable, str(step3_script), str(pdf_path)], check=True)
    
    # Validate output in S3
    s3_key_logic = get_s3_key("processed", "final_logic_output.json")
    if not file_exists_in_s3(s3_key_logic):
        raise RuntimeError(f"final_logic_output.json was not created in S3: {s3_key_logic}")
    
    print("✅ Step 3/3: Logic extraction completed!")
    
    # Get grouped tariffs key from step 2
    step2_output = ti.xcom_pull(task_ids='group_tariffs_by_service_class')
    s3_key_grouped = step2_output.get('s3_key') if step2_output else get_s3_key("processed", "grouped_tariffs.json")
    
    print("\n" + "="*60)
    print("✅ TARIFF PIPELINE COMPLETED SUCCESSFULLY!")
    print("="*60)
    print(f"📄 Grouped Tariffs: s3://{s3_key_grouped}")
    print(f"🎯 Final Logic Output: s3://{s3_key_logic}")
    print("="*60 + "\n")
    
    return {
        "grouped_tariffs": s3_key_grouped,
        "final_logic": s3_key_logic
    }


# Define the DAG
with DAG(
    dag_id='tariff_pipeline',
    default_args=default_args,
    description='Tariff Analysis Pipeline - Extract and process tariff documents in multiple steps',
    schedule=None,  # Manual trigger only (Airflow 3.x uses 'schedule' not 'schedule_interval')
    start_date=datetime(2025, 12, 1),
    catchup=False,
    tags=['tariff', 'analysis', 'llm'],
) as dag:
    
    # Task 1: Extract text from PDF
    task_extract_text = PythonOperator(
        task_id='extract_text_from_pdf',
        python_callable=extract_text_from_pdf,
    )
    
    # Task 2: Group tariffs by service class
    task_group_tariffs = PythonOperator(
        task_id='group_tariffs_by_service_class',
        python_callable=group_tariffs_by_service_class,
    )
    
    # Task 3: Extract logic using LLM
    task_extract_logic = PythonOperator(
        task_id='extract_logic_using_llm',
        python_callable=extract_logic_using_llm,
    )
    
    # Define task dependencies (sequential flow)
    task_extract_text >> task_group_tariffs >> task_extract_logic
