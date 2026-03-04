from typing import Literal

from pydantic import BaseModel


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
