from fastapi import APIRouter
from typing import Literal
from pydantic import BaseModel

from src.services.report_service import ReportService


class ReportAccountsResponse(BaseModel):
    accounts: list[str]


class OverrideGridRow(BaseModel):
    bill_date: str
    billed_kwh: float
    billed_demand: float
    bill_amount: float
    service_class: str
    override_tra: float = 0.0
    override_rdm: float = 0.0


class OverrideGridResponse(BaseModel):
    account_id: str
    sc_code: str
    rows: list[OverrideGridRow]


class ReportsCalculateRequest(BaseModel):
    account_id: str
    sc_code: str
    rows: list[OverrideGridRow]


class ReportResultRow(BaseModel):
    bill_date: str
    service_class: str
    kwh: float
    demand_kw: float
    actual_bill: float
    tra: float
    rdm: float
    expected_bill: float
    variance: float
    status: Literal["SUCCESS", "SKIPPED", "FAILED"] | str


class ReportsCalculateResponse(BaseModel):
    rows: list[ReportResultRow]
    total_actual: float
    total_expected: float
    total_variance: float

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
