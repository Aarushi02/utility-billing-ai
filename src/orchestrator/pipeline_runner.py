from pathlib import Path
import subprocess
import sys
import uuid

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.aws_app import file_exists_in_s3, get_s3_key


def _run_step(cmd, step_name, timeout=600):
    """
    Run a subprocess step with live output streaming to terminal.
    Captures output into a log file alongside streaming it.
    Returns the CompletedProcess result.
    """
    print(f"\n{'='*60}")
    print(f"  {step_name}")
    print(f"{'='*60}")

    log_path = PROJECT_ROOT / "logs" / f"{step_name.replace(' ', '_').lower()}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(log_path, "w") as log_file:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,   # capture stdout
                stderr=subprocess.STDOUT, # merge stderr into stdout
                text=True,
                timeout=timeout,
                bufsize=1,                # line buffered
            )

            # Write to log and print to terminal simultaneously
            for line in result.stdout.splitlines():
                print(line)
                log_file.write(line + "\n")

        return result

    except subprocess.TimeoutExpired:
        raise RuntimeError(
            f"{step_name} timed out after {timeout} seconds. "
            f"Check log: {log_path}"
        )


def run_tariff_pipeline(pdf_path: Path, raw_bill_document_id: int = None):

    # ----------------------------------------------------------
    # Setup
    # ----------------------------------------------------------
    pdf_path = Path(pdf_path)
    pdf_filename = pdf_path.name

    print(f"\nStarting Tariff Pipeline")
    print(f"PDF:  {pdf_path}")
    print(f"Doc ID: {raw_bill_document_id or 'None'}")

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    # Unique job ID to prevent S3 collisions if multiple uploads happen simultaneously
    job_id = str(uuid.uuid4())[:8]
    print(f"Job ID: {job_id}")

    # ----------------------------------------------------------
    # Resolve script paths
    # ----------------------------------------------------------
    agent_dir = PROJECT_ROOT / "src" / "agents" / "tariff_analysis_agent"

    step1 = agent_dir / "pagewise_text_extractor.py"
    step2 = agent_dir / "group_extracted_raw_text.py"
    step3 = agent_dir / "extract_logic_llm_call.py"

    for script in [step1, step2, step3]:
        if not script.exists():
            raise FileNotFoundError(f"Missing script: {script}")

    # ----------------------------------------------------------
    # Step 1: Extract text page by page from PDF
    # ----------------------------------------------------------
    result = _run_step(
        cmd=[sys.executable, "-u", str(step1), str(pdf_path)],
        step_name="Step 1/3: Extracting text from PDF pages",
        timeout=600,  # 10 minutes — pdfplumber on 684 pages should be well under this
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Step 1 failed with exit code {result.returncode}.\n"
            f"Output:\n{result.stdout}"
        )

    s3_key_raw = get_s3_key("processed", "raw_extracted_tarif.json")
    if not file_exists_in_s3(s3_key_raw):
        raise RuntimeError(
            f"Step 1 completed but raw_extracted_tarif.json not found in S3.\n"
            f"Expected key: {s3_key_raw}"
        )

    print(f"\n✅ Step 1 complete. Output in S3: {s3_key_raw}")

    # ----------------------------------------------------------
    # Step 2: Group extracted text by service classification
    # ----------------------------------------------------------
    result = _run_step(
        cmd=[sys.executable, "-u", str(step2)],
        step_name="Step 2/3: Grouping tariffs by service class",
        timeout=120,  # 2 minutes — this is pure text processing, should be fast
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Step 2 failed with exit code {result.returncode}.\n"
            f"Output:\n{result.stdout}"
        )

    s3_key_grouped = get_s3_key("processed", "grouped_tariffs.json")
    if not file_exists_in_s3(s3_key_grouped):
        raise RuntimeError(
            f"Step 2 completed but grouped_tariffs.json not found in S3.\n"
            f"Expected key: {s3_key_grouped}"
        )

    print(f"\n✅ Step 2 complete. Output in S3: {s3_key_grouped}")

    # ----------------------------------------------------------
    # Step 3: Extract tariff logic using LLM
    # ----------------------------------------------------------

    # Fix: pass raw_bill_document_id as sys.argv[2] so the script can read it
    cmd_step3 = [sys.executable, "-u", str(step3), str(pdf_path)]
    if raw_bill_document_id is not None:
        cmd_step3.append(str(raw_bill_document_id))

    result = _run_step(
        cmd=cmd_step3,
        step_name="Step 3/3: Extracting tariff logic via LLM",
        timeout=1800,  # 30 minutes — LLM calls per SC code, this is the slow step
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Step 3 failed with exit code {result.returncode}.\n"
            f"Output:\n{result.stdout}"
        )

    s3_key_logic = get_s3_key("processed", "final_logic_output.json")
    if not file_exists_in_s3(s3_key_logic):
        raise RuntimeError(
            f"Step 3 completed but final_logic_output.json not found in S3.\n"
            f"Expected key: {s3_key_logic}"
        )

    print(f"\n✅ Step 3 complete. Output in S3: {s3_key_logic}")

    # ----------------------------------------------------------
    # Done
    # ----------------------------------------------------------
    print("\n" + "=" * 60)
    print("  TARIFF PIPELINE COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    print(f"  PDF:             {pdf_filename}")
    print(f"  Job ID:          {job_id}")
    print(f"  Grouped Tariffs: s3://{s3_key_grouped}")
    print(f"  Final Logic:     s3://{s3_key_logic}")
    print("=" * 60 + "\n")

    return {
        "job_id": job_id,
        "grouped_tariffs": s3_key_grouped,
        "final_logic": s3_key_logic,
    }