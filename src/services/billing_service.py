from src.repositories.billing_repository import BillingRepository


class BillingService:
    def __init__(self, repository: BillingRepository | None = None) -> None:
        self.repository = repository or BillingRepository()

    def get_accounts(self) -> list[str]:
        return self.repository.list_accounts()

    def get_bills(self, account_id: str) -> list[dict]:
        return self.repository.list_bills(account_id)

    def get_bill_issues(self, account_id: str, issue_type: str | None = None) -> list[dict]:
        return self.repository.list_bill_issues(account_id, issue_type)
