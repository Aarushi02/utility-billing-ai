from fastapi import APIRouter
from datetime import datetime
from pydantic import BaseModel

from src.services.upload_service import UploadService


class RawDocumentCreateRequest(BaseModel):
    file_name: str
    file_type: str | None = None
    upload_date: datetime | None = None
    source: str | None = None
    status: str | None = "uploaded"


class RawDocumentCreateResponse(BaseModel):
    id: int | None = None


class RawDocumentListItemResponse(BaseModel):
    id: int
    file_name: str
    file_type: str | None = None
    upload_date: datetime | None = None
    source: str | None = None
    status: str | None = None


router = APIRouter(prefix="/uploads")
service = UploadService()


@router.post("/raw-documents", response_model=RawDocumentCreateResponse)
def create_raw_document(payload: RawDocumentCreateRequest) -> RawDocumentCreateResponse:
    document_id = service.create_raw_document(payload.model_dump())
    return RawDocumentCreateResponse(id=document_id)


@router.get("/raw-documents", response_model=list[RawDocumentListItemResponse])
def list_raw_documents() -> list[RawDocumentListItemResponse]:
    documents = service.list_raw_documents()
    return [
        RawDocumentListItemResponse(
            id=doc.id,
            file_name=doc.file_name,
            file_type=doc.file_type,
            upload_date=doc.upload_date,
            source=doc.source,
            status=doc.status,
        )
        for doc in documents
    ]
