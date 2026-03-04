from fastapi import APIRouter
from pydantic import BaseModel

from src.services.billing_service import BillingService


class BillAccountsResponse(BaseModel):
    accounts: list[str]


class BillsResponse(BaseModel):
    account_id: str
    bills: list[dict[str, object]]


class BillIssuesResponse(BaseModel):
    account_id: str
    issues: list[dict[str, object]]


router = APIRouter(prefix="/bills")
service = BillingService()


@router.get("/accounts", response_model=BillAccountsResponse)
def list_accounts() -> BillAccountsResponse:
    return BillAccountsResponse(accounts=service.get_accounts())


@router.get("", response_model=BillsResponse)
def list_bills(account_id: str) -> BillsResponse:
    bills = service.get_bills(account_id)
    return BillsResponse(account_id=account_id, bills=bills)


@router.get("/issues", response_model=BillIssuesResponse)
def list_bill_issues(account_id: str, issue_type: str | None = None) -> BillIssuesResponse:
    issues = service.get_bill_issues(account_id, issue_type)
    return BillIssuesResponse(account_id=account_id, issues=issues)
