from typing import Any

from pydantic import BaseModel


class BillAccountsResponse(BaseModel):
    accounts: list[str]


class BillsResponse(BaseModel):
    account_id: str
    bills: list[dict[str, Any]]


class BillIssuesResponse(BaseModel):
    account_id: str
    issues: list[dict[str, Any]]
