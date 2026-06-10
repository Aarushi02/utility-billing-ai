from pathlib import Path
import subprocess
import sys
import uuid
import threading

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.aws_app import file_exists_in_s3, get_s3_key
from src.utils.job_store import update_job_status, cleanup_job  # ← new import


def _run_step(cmd, step_name, cancel_event: threading.Event, timeout=600):  # ← add cancel_event param
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
            process = subprocess.Popen(             # ← Popen instead of run so we can kill it
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            # Stream output line by line, checking cancel between each line
            for line in process.stdout:
                print(line, end="")
                log_file.write(line)

                if cancel_event.is_set():           # ← check cancel during streaming
                    process.kill()
                    print(f"\n⚠️  {step_name} cancelled — process killed.")
                    return None                     # ← None signals cancellation to caller

            process.wait(timeout=timeout)
            return process

    except subprocess.TimeoutExpired:
        process.kill()
        raise RuntimeError(
            f"{step_name} timed out after {timeout} seconds. "
            f"Check log: {log_path}"
        )


def run_tariff_pipeline(
    pdf_path: Path,
    raw_bill_document_id: int = None,
    job_id: str = None,                            # ← new param
    cancel_event: threading.Event = None,          # ← new param
):
    # ----------------------------------------------------------
    # Setup
    # ----------------------------------------------------------
    pdf_path = Path(pdf_path)
    pdf_filename = pdf_path.name
    doc_key = str(raw_bill_document_id or pdf_filename)

    # Use provided job_id/cancel_event (from router) or create standalone ones
    job_id = job_id or str(uuid.uuid4())[:8]
    cancel_event = cancel_event or threading.Event()

    print(f"\nStarting Tariff Pipeline")
    print(f"PDF:  {pdf_path}")
    print(f"Doc ID: {raw_bill_document_id or 'None'}")
    print(f"Job ID: {job_id}")

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

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

    try:
        # ----------------------------------------------------------
        # Step 1: Extract text page by page from PDF
        # ----------------------------------------------------------
        if cancel_event.is_set():                  # ← check before starting step
            print("⚠️  Job cancelled before Step 1.")
            return {"job_id": job_id, "status": "cancelled"}

        update_job_status(job_id, step=1, message="Extracting text from PDF pages...")

        result = _run_step(
            cmd=[sys.executable, "-u", str(step1), str(pdf_path)],
            step_name="Step 1/3: Extracting text from PDF pages",
            cancel_event=cancel_event,             # ← pass down
            timeout=600,
        )

        if result is None:                         # ← None = cancelled inside _run_step
            return {"job_id": job_id, "status": "cancelled"}

        if result.returncode != 0:
            raise RuntimeError(f"Step 1 failed with exit code {result.returncode}.")

        s3_key_raw = get_s3_key("processed", "raw_extracted_tarif.json")
        if not file_exists_in_s3(s3_key_raw):
            raise RuntimeError(f"Step 1 completed but raw_extracted_tarif.json not found in S3.")

        print(f"\n✅ Step 1 complete. Output in S3: {s3_key_raw}")

        # ----------------------------------------------------------
        # Step 2: Group extracted text by service classification
        # ----------------------------------------------------------
        if cancel_event.is_set():                  # ← check before starting step
            print("⚠️  Job cancelled before Step 2.")
            return {"job_id": job_id, "status": "cancelled"}

        update_job_status(job_id, step=2, message="Grouping tariffs by service class...")

        result = _run_step(
            cmd=[sys.executable, "-u", str(step2)],
            step_name="Step 2/3: Grouping tariffs by service class",
            cancel_event=cancel_event,             # ← pass down
            timeout=120,
        )

        if result is None:
            return {"job_id": job_id, "status": "cancelled"}

        if result.returncode != 0:
            raise RuntimeError(f"Step 2 failed with exit code {result.returncode}.")

        s3_key_grouped = get_s3_key("processed", "grouped_tariffs.json")
        if not file_exists_in_s3(s3_key_grouped):
            raise RuntimeError(f"Step 2 completed but grouped_tariffs.json not found in S3.")

        print(f"\n✅ Step 2 complete. Output in S3: {s3_key_grouped}")

        # ----------------------------------------------------------
        # Step 3: Extract tariff logic using LLM
        # ----------------------------------------------------------
        if cancel_event.is_set():                  # ← check before starting step
            print("⚠️  Job cancelled before Step 3.")
            return {"job_id": job_id, "status": "cancelled"}

        update_job_status(job_id, step=3, message="Extracting tariff logic via LLM...")

        cmd_step3 = [sys.executable, "-u", str(step3), str(pdf_path)]
        if raw_bill_document_id is not None:
            cmd_step3.append(str(raw_bill_document_id))

        result = _run_step(
            cmd=cmd_step3,
            step_name="Step 3/3: Extracting tariff logic via LLM",
            cancel_event=cancel_event,             # ← pass down
            timeout=1800,
        )

        if result is None:
            return {"job_id": job_id, "status": "cancelled"}

        if result.returncode != 0:
            raise RuntimeError(f"Step 3 failed with exit code {result.returncode}.")

        s3_key_logic = get_s3_key("processed", "final_logic_output.json")
        if not file_exists_in_s3(s3_key_logic):
            raise RuntimeError(f"Step 3 completed but final_logic_output.json not found in S3.")

        print(f"\n✅ Step 3 complete. Output in S3: {s3_key_logic}")

        # ----------------------------------------------------------
        # Done
        # ----------------------------------------------------------
        print("\n" + "=" * 60)
        print("  TARIFF PIPELINE COMPLETED SUCCESSFULLY!")
        print("=" * 60)

        return {
            "job_id": job_id,
            "status": "completed",
            "grouped_tariffs": s3_key_grouped,
            "final_logic": s3_key_logic,
        }

    finally:
        cleanup_job(doc_key, job_id)               # ← always clean up active job registry