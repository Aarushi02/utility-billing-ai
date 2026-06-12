# src/agents/tariff_analysis/extract_pdf.py
"""
Step 1.3 – Extract text and tables from PDF (config-driven).
This creates a machine-readable JSON used by later stages.
"""

import logging
import pdfplumber
import signal
import json
from pathlib import Path
import sys
import glob

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.utils.aws_app import upload_json_to_s3, get_s3_key

PROJECT_ROOT = Path(__file__).resolve().parents[3]

# Accept PDF path from command line argument, otherwise use default
if len(sys.argv) > 1:
    PDF_PATH = Path(sys.argv[1])
    print(f" Using PDF from argument: {PDF_PATH}")
    logging.info(f" Using PDF from argument: {PDF_PATH}")
else:
    PDF_PATH = Path("UNDEFINED_NO_PDF_PROVIDED")
    print("No PDF path provided as argument; using default.")
    logging.info(" No PDF path provided as argument; using default.")

OUTPUT_PATH = PROJECT_ROOT / Path("data/processed/raw_extracted_tarif.json")


def _extract_tables_safe(page, timeout_sec: int = 10) -> list:
    """
    Extract tables from a page with a timeout.
    Returns [] if extraction hangs or fails — never blocks the pipeline.
    """
    def _handler(signum, frame):
        raise TimeoutError(f"extract_tables timed out on page {page.page_number}")

    signal.signal(signal.SIGALRM, _handler)
    signal.alarm(timeout_sec)
    try:
        raw_tables = page.extract_tables() or []
        return [t for t in raw_tables if t]
    except TimeoutError as e:
        print(f"⚠️  Page {page.page_number}: {e} — skipping tables for this page")
        return []
    except Exception as e:
        print(f"⚠️  Page {page.page_number}: extract_tables error ({e}) — skipping tables")
        return []
    finally:
        signal.alarm(0)  # always cancel the alarm


def extract_with_pdfplumber(pdf_path: Path, start_page: int = None, end_page: int = None):
    pages_data = []

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        start_page = start_page or 1
        end_page = end_page or total_pages

        print(f"📄 Total pages to extract: {end_page - start_page + 1}")

        for i in range(start_page - 1, end_page):
            page = pdf.pages[i]

            # ── Text extraction ───────────────────────────────────────────────
            try:
                text = page.extract_text() or ""
            except Exception as e:
                print(f"⚠️  Page {page.page_number}: extract_text error ({e}) — skipping text")
                text = ""

            # ── Table extraction with timeout ─────────────────────────────────
            tables = _extract_tables_safe(page, timeout_sec=10)

            pages_data.append({
                "page_number": page.page_number,
                "text": text.strip(),
                "tables": tables,
            })

            # ── Progress log every 50 pages ───────────────────────────────────
            if page.page_number % 50 == 0 or page.page_number == end_page:
                print(f"  ✅ Processed page {page.page_number}/{end_page}")

    return pages_data


def save_output(data, path: Path):
    # Upload directly to S3 (no local storage)
    s3_key = get_s3_key("processed", path.name)
    if upload_json_to_s3({"pages": data}, s3_key):
        print(f"✅ Uploaded to S3: {s3_key}")
    else:
        raise Exception(f"Failed to upload to S3: {s3_key}")


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

    print("🔍 Extracting text and tables with pdfplumber...")
    pages_data = extract_with_pdfplumber(pdf_to_use)

    print("💾 Saving structured output...")
    save_output(pages_data, OUTPUT_PATH)

    print("✅ Done. Proceed to Step 1.4 – Dynamic Section Segmentation.")