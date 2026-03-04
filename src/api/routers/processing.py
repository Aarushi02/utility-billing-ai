from fastapi import APIRouter
from pydantic import BaseModel

from src.services.processing_service import ProcessingService


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
    grouped_tariffs: str | None = None
    final_logic: str | None = None


router = APIRouter(prefix="/processing")
service = ProcessingService()


@router.post("/bills/run", response_model=BillProcessResponse)
def run_bill_processing(payload: BillProcessRequest) -> BillProcessResponse:
    result = service.process_bill(payload.s3_key, document_id=payload.document_id)
    return BillProcessResponse(**result)


@router.post("/tariffs/run", response_model=TariffProcessResponse)
def run_tariff_processing(payload: TariffProcessRequest) -> TariffProcessResponse:
    result = service.process_tariff(payload.s3_key, raw_bill_document_id=payload.raw_bill_document_id)
    return TariffProcessResponse(**result)
