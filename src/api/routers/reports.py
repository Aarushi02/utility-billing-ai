from fastapi import APIRouter
from fastapi.encoders import jsonable_encoder
from typing import Literal
from pydantic import BaseModel

from src.services.report_service import ReportService
from fastapi.responses import JSONResponse
import math
import numpy as np
import pandas as pd

print("=== LOADED REPORTS ROUTER DEBUG VERSION ===")

router = APIRouter(prefix="/reports")
service = ReportService()


class ReportAccountsResponse(BaseModel):
    accounts: list[str]


class OverrideGridRow(BaseModel):
    bill_date: str
    billed_kwh: float | None = None
    billed_demand: float | None = None
    bill_amount: float | None = None
    service_class: str
    override_tra: float | None = None
    override_rdm: float | None = None
    override_sbc: float | None = None
    override_ram: float | None = None


class OverrideGridResponse(BaseModel):
    account_id: str | None = None
    sc_code: str | None = None
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

class ReportsSaveRequest(BaseModel):
    account_id: str
    sc_code: str
    rows: list[OverrideGridRow]


@router.get("/accounts", response_model=ReportAccountsResponse)
def get_report_accounts() -> ReportAccountsResponse:
    return ReportAccountsResponse(accounts=service.list_accounts())


@router.get("/grid")
def get_override_grid(account_id: str | None = None, sc_code: str | None = None):
    rows = service.load_override_grid(sc_code=sc_code)

    bad_values = []
    for i, row in enumerate(rows):
        for key, value in row.items():
            if value is None:
                continue

            if isinstance(value, (float, np.floating)):
                val = float(value)
                if math.isnan(val) or math.isinf(val):
                    bad_values.append(
                        {"row_index": i, "column": key, "value": str(value)}
                    )

    if bad_values:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Non-JSON-safe numeric values found",
                "bad_values": bad_values[:20],
            },
        )

    return JSONResponse(
        content={
            "account_id": account_id,
            "sc_code": sc_code,
            "rows": rows,
        }
    )


@router.post("/save-overrides")
def save_overrides(payload: ReportsSaveRequest):
    save_result = service.save_overrides(
        sc_code=payload.sc_code,
        rows=[row.model_dump() for row in payload.rows],
    )

    refreshed_rows = service.load_override_grid(sc_code=payload.sc_code)

    return {
        "saved": save_result,
        "account_id": payload.account_id,
        "sc_code": payload.sc_code,
        "rows": refreshed_rows,
    }