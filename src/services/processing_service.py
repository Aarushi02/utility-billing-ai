import os
from pathlib import Path

import pandas as pd

from src.utils.aws_app import download_to_temp


class ProcessingService:
    def process_bill(self, s3_key: str, document_id: int | None = None) -> dict:
        temp_path = download_to_temp(s3_key)
        if not temp_path:
            raise ValueError(f"Failed to download from S3: {s3_key}")

        try:
            from src.agents.document_processor_agent.utility_bill_doc_processor import process_bill

            dataframe, total_anomalies = process_bill(Path(temp_path), document_id=document_id)
            normalized_df = dataframe.astype(object).where(pd.notna(dataframe), None)
            return {
                "total_anomalies": int(total_anomalies),
                "rows": normalized_df.to_dict(orient="records"),
            }
        finally:
            try:
                os.unlink(temp_path)
            except OSError:
                pass

    def process_tariff(self, s3_key: str, raw_bill_document_id: int | None = None) -> dict:
        temp_path = download_to_temp(s3_key)
        if not temp_path:
            raise ValueError(f"Failed to download from S3: {s3_key}")

        try:
            from src.orchestrator.pipeline_runner import run_tariff_pipeline

            return run_tariff_pipeline(Path(temp_path), raw_bill_document_id=raw_bill_document_id)
        finally:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
