# src/agents/tariff_analysis/extract_pdf.py
"""
Step 1.3 – Extract text and tables from PDF (config-driven).
Processes in batches to avoid OOM on large PDFs.
"""

import logging
import pdfplumber
import signal
import json
from pathlib import Path
import sys
import glob

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.utils.aws_app import upload_json_to_s3, get_s3_key, download_json_from_s3

PROJECT_ROOT = Path(__file__).resolve().parents[3]

if len(sys.argv) > 1:
    PDF_PATH = Path(sys.argv[1])
    print(f" Using PDF from argument: {PDF_PATH}")
    logging.info(f" Using PDF from argument: {PDF_PATH}")
else:
    PDF_PATH = Path("UNDEFINED_NO_PDF_PROVIDED")
    print("No PDF path provided as argument; using default.")
    logging.info(" No PDF path provided as argument; using default.")

OUTPUT_PATH = PROJECT_ROOT / Path("data/processed/raw_extracted_tarif.json")

BATCH_SIZE = 50  # pages per batch — keeps memory under ~200MB


def _extract_tables_safe(page, timeout_sec: int = 10) -> list:
    """Extract tables with timeout — returns [] if it hangs or fails."""
    def _handler(signum, frame):
        raise TimeoutError(f"extract_tables timed out on page {page.page_number}")

    signal.signal(signal.SIGALRM, _handler)
    signal.alarm(timeout_sec)
    try:
        raw_tables = page.extract_tables() or []
        return [t for t in raw_tables if t]
    except TimeoutError as e:
        print(f"⚠️  Page {page.page_number}: {e} — skipping tables")
        return []
    except Exception as e:
        print(f"⚠️  Page {page.page_number}: extract_tables error ({e}) — skipping tables")
        return []
    finally:
        signal.alarm(0)


def extract_and_upload_in_batches(pdf_path: Path, batch_size: int = BATCH_SIZE):
    """
    Extract PDF in batches, uploading each batch to S3 immediately.
    Merges all batches into final output at the end.
    Final output key: processed/raw_extracted_tarif.json
    """
    s3_key_final = get_s3_key("processed", "raw_extracted_tarif.json")
    all_pages = []

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        print(f"📄 Total pages: {total_pages} — processing in batches of {batch_size}")

        for batch_start in range(0, total_pages, batch_size):
            batch_end = min(batch_start + batch_size, total_pages)
            batch_pages = []

            for i in range(batch_start, batch_end):
                page = pdf.pages[i]

                # ── Text ─────────────────────────────────────────────────────
                try:
                    text = page.extract_text() or ""
                except Exception as e:
                    print(f"⚠️  Page {page.page_number}: extract_text error ({e})")
                    text = ""

                # ── Tables with timeout ───────────────────────────────────────
                tables = _extract_tables_safe(page, timeout_sec=10)

                batch_pages.append({
                    "page_number": page.page_number,
                    "text": text.strip(),
                    "tables": tables,
                })

            # Accumulate batch results
            all_pages.extend(batch_pages)

            # Free batch memory immediately
            del batch_pages

            print(f"  ✅ Processed pages {batch_start + 1}–{batch_end}/{total_pages}")

    # Upload complete result to S3
    print(f"💾 Uploading {len(all_pages)} pages to S3...")
    if not upload_json_to_s3({"pages": all_pages}, s3_key_final):
        raise Exception(f"Failed to upload final output to S3: {s3_key_final}")

    print(f"✅ Uploaded to S3: {s3_key_final}")
    return s3_key_final


if __name__ == "__main__":
    cli_pdf = Path(sys.argv[1]) if len(sys.argv) > 1 else None

    if cli_pdf and cli_pdf.exists():
        pdf_to_use = cli_pdf
    elif PDF_PATH.exists():
        pdf_to_use = PDF_PATH
    else:
        candidates = sorted(glob.glob(str(PROJECT_ROOT / "data" / "raw" / "*.pdf")))
        if len(candidates) == 1:
            pdf_to_use = Path(candidates[0])
            print(f"ℹ️  Using found PDF: {pdf_to_use}")
        elif len(candidates) > 1:
            print("❌ Multiple PDFs found under data/raw/; pass the desired file as an argument.")
            for p in candidates:
                print(" -", p)
            sys.exit(1)
        else:
            print(f"❌ File not found: {PDF_PATH}")
            existing = sorted(glob.glob(str(PROJECT_ROOT / "data" / "raw" / "*")))
            if existing:
                print("Files in data/raw/:")
                for p in existing:
                    print(" -", p)
            else:
                print("data/raw/ is empty or missing.")
            sys.exit(1)

    print("🔍 Extracting text and tables with pdfplumber (batched)...")
    extract_and_upload_in_batches(pdf_to_use, batch_size=BATCH_SIZE)

    print("✅ Done. Proceed to Step 1.4 – Dynamic Section Segmentation.")