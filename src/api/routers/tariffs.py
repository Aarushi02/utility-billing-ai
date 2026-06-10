from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import threading

from src.services.tariff_service import TariffService
from src.utils.job_store import register_job, complete_job, get_job_status, cleanup_job
from src.orchestrator.pipeline_runner import run_tariff_pipeline


class TariffScCodesResponse(BaseModel):
    sc_codes: list[str]


class TariffVersionsResponse(BaseModel):
    sc_code: str
    versions: list[str]


class TariffLogicResponse(BaseModel):
    sc_code: str
    effective_date: str
    logic: dict[str, object]


# ── New: request/response models for pipeline run ────────────────────────────
class TariffRunRequest(BaseModel):
    doc_id: int | None = None
    filename: str
    pdf_path: str


class TariffRunResponse(BaseModel):
    job_id: str
    status: str


# ── New: active thread registry so we can cancel on re-submit ────────────────
_active_threads: dict[str, threading.Thread] = {}
_threads_lock = threading.Lock()

# ─────────────────────────────────────────────────────────────────────────────

router = APIRouter(prefix="/tariffs")
service = TariffService()


# ── Existing endpoints (unchanged) ───────────────────────────────────────────

@router.get("/sc-codes", response_model=TariffScCodesResponse)
def get_sc_codes() -> TariffScCodesResponse:
    return TariffScCodesResponse(sc_codes=service.get_sc_codes())


@router.get("/{sc_code}/versions", response_model=TariffVersionsResponse)
def get_versions(sc_code: str) -> TariffVersionsResponse:
    versions = service.get_versions_for_sc(sc_code)
    if not versions:
        raise HTTPException(status_code=404, detail=f"No versions found for sc_code={sc_code}")
    return TariffVersionsResponse(sc_code=sc_code, versions=versions)


@router.get("/{sc_code}/versions/{effective_date}", response_model=TariffLogicResponse)
def get_logic(sc_code: str, effective_date: str) -> TariffLogicResponse:
    logic = service.get_logic_for_sc_version(sc_code, effective_date)
    if logic is None:
        raise HTTPException(
            status_code=404,
            detail=f"No logic found for sc_code={sc_code}, effective_date={effective_date}",
        )
    return TariffLogicResponse(
        sc_code=sc_code,
        effective_date=effective_date,
        logic=logic,
    )


# ── New: pipeline run + status endpoints ─────────────────────────────────────

@router.post("/run", response_model=TariffRunResponse)
def run_tariff(request: TariffRunRequest) -> TariffRunResponse:
    doc_key = str(request.doc_id or request.filename)

    # Register new job — cancels any existing job for this doc_key
    cancel_event, job_id = register_job(doc_key)

    # Run pipeline in a background thread so the endpoint returns immediately
    def _run():
        try:
            run_tariff_pipeline(
                pdf_path=request.pdf_path,
                raw_bill_document_id=request.doc_id,
                job_id=job_id,
                cancel_event=cancel_event,
            )
            complete_job(job_id)
        except Exception as e:
            from src.utils.job_store import fail_job
            fail_job(job_id, str(e))
        finally:
            with _threads_lock:
                _active_threads.pop(doc_key, None)

    thread = threading.Thread(target=_run, daemon=True)
    with _threads_lock:
        _active_threads[doc_key] = thread
    thread.start()

    return TariffRunResponse(job_id=job_id, status="started")


@router.get("/status/{job_id}")
def get_run_status(job_id: str) -> dict:
    status = get_job_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    return status