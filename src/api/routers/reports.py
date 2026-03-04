from fastapi import APIRouter

from src.api.schemas.reports import (
    OverrideGridResponse,
    ReportAccountsResponse,
    ReportsCalculateRequest,
    ReportsCalculateResponse,
)
from src.services.report_service import ReportService

router = APIRouter(prefix="/reports")
service = ReportService()


@router.get("/accounts", response_model=ReportAccountsResponse)
def get_report_accounts() -> ReportAccountsResponse:
    return ReportAccountsResponse(accounts=service.list_accounts())


@router.get("/grid", response_model=OverrideGridResponse)
def get_override_grid(account_id: str, sc_code: str) -> OverrideGridResponse:
    rows = service.load_override_grid(account_id=account_id, sc_code=sc_code)
    return OverrideGridResponse(account_id=account_id, sc_code=sc_code, rows=rows)


@router.post("/calculate", response_model=ReportsCalculateResponse)
def calculate_report(payload: ReportsCalculateRequest) -> ReportsCalculateResponse:
    result = service.calculate_expected_bill(
        account_id=payload.account_id,
        sc_code=payload.sc_code,
        rows=[row.model_dump() for row in payload.rows],
    )
    return ReportsCalculateResponse(**result)
