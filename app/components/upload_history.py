import streamlit as st
import pandas as pd
from pathlib import Path
import requests
import time

from src.utils.config import get_env
from src.utils.aws_app import (
    get_s3_key,
    file_exists_in_s3,
    list_files_in_s3_with_meta,
)


API_BASE_URL = get_env("API_BASE_URL", "http://localhost:8000")


def _fetch_raw_documents() -> list[dict]:
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            response = requests.get(f"{API_BASE_URL}/api/v1/uploads/raw-documents", timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            last_exc = exc
            if attempt < 2:
                time.sleep(1 + attempt)
                continue
            raise

    if last_exc:
        raise last_exc

    return []


def render_upload_history():
    """Render a simple upload history table for previously uploaded documents."""
    st.title("📜 Upload History")
    st.caption("Review previously uploaded documents")

    try:
        raw_docs = _fetch_raw_documents()

        # -------------------------
        # Table 1: DB records + S3 status
        # -------------------------
        if raw_docs:
            rows = []
            db_keys = set()

            for doc in raw_docs:
                file_name = doc.get("file_name", "")
                s3_key = get_s3_key("raw", file_name)
                exists = file_exists_in_s3(s3_key)
                db_keys.add(s3_key)
                upload_date = doc.get("upload_date")
                if upload_date:
                    upload_date = str(upload_date).replace("T", " ")[:16]
                else:
                    upload_date = "N/A"

                rows.append({
                    "File Name": file_name,
                    "Source": doc.get("source"),
                    "Upload Date": upload_date,
                    "S3 Exists": "✅" if exists else "❌",
                })

            st.markdown("### 📄 Database Records")
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("📭 No database records found")

        # -------------------------
        # Table 2: S3-only files (not in DB)
        # -------------------------
        s3_items = list_files_in_s3_with_meta("data/raw/")
        if s3_items:
            db_keys = db_keys if 'db_keys' in locals() else set()
            orphan_items = [item for item in s3_items if item.get("Key") not in db_keys]

            if orphan_items:
                st.markdown("### 🗂️ S3 Files Not In Database")
                orphan_rows = []
                for item in orphan_items:
                    key = item.get("Key")
                    last_modified = item.get("LastModified")
                    file_name = Path(key).name if key else ""
                    orphan_rows.append({
                        "File Name": file_name,
                        "Upload Date": last_modified.strftime("%Y-%m-%d %H:%M") if last_modified else "N/A",
                        "S3 Exists": "✅",
                    })
                df_orphan = pd.DataFrame(orphan_rows)
                st.dataframe(df_orphan, use_container_width=True, hide_index=True)
        
        if (not raw_docs) and (not s3_items):
            st.info("📭 No documents uploaded yet")

    except Exception as exc:
        st.error(f"Unable to load upload history: {exc}")
