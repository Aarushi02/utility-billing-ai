from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import threading

from src.services.processing_service import ProcessingService
from src.utils.job_store import register_job, complete_job, fail_job, get_job_status
from src.utils.aws_app import download_to_temp
from src.orchestrator.pipeline_runner import run_tariff_pipeline


class BillProcessRequest(BaseModel):
    s3_key: str
    document_id: int | None = None


class BillProcessResponse(BaseModel):
    total_anomalies: int
    rows: list[dict[str, object]]


class TariffProcessRequest(BaseModel):
    s3_key: str
    raw_bill_document_id: int | None = None


class TariffProcessResponse(BaseModel):
    job_id: str
    status: str


_active_threads: dict[str, threading.Thread] = {}
_threads_lock = threading.Lock()

router = APIRouter(prefix="/processing")
service = ProcessingService()


@router.post("/bills/run", response_model=BillProcessResponse)
def run_bill_processing(payload: BillProcessRequest) -> BillProcessResponse:
    result = service.process_bill(payload.s3_key, document_id=payload.document_id)
    return BillProcessResponse(**result)


# ── Status endpoint BEFORE /tariffs/run to avoid route conflicts ──────────────
@router.get("/tariffs/status/{job_id}")
def get_tariff_status(job_id: str) -> dict:
    status = get_job_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    return status


# ── Last-write-wins: cancels old job, starts new one in background thread ─────
@router.post("/tariffs/run", response_model=TariffProcessResponse)
def run_tariff_processing(payload: TariffProcessRequest) -> TariffProcessResponse:
    doc_key = str(payload.raw_bill_document_id or payload.s3_key)

    cancel_event, job_id = register_job(doc_key)

    def _run():
        try:
            pdf_path = download_to_temp(payload.s3_key)
            if not pdf_path:
                fail_job(job_id, f"Failed to download PDF from S3: {payload.s3_key}")
                return

            run_tariff_pipeline(
                pdf_path=pdf_path,
                raw_bill_document_id=payload.raw_bill_document_id,
                job_id=job_id,
                cancel_event=cancel_event,
            )
            complete_job(job_id)

        except Exception as e:
            fail_job(job_id, str(e))
        finally:
            with _threads_lock:
                _active_threads.pop(doc_key, None)

    thread = threading.Thread(target=_run, daemon=True)
    with _threads_lock:
        _active_threads[doc_key] = thread
    thread.start()

    return TariffProcessResponse(job_id=job_id, status="started")