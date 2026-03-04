import pandas as pd

from src.database.utils.user_bills_utils import (
    fetch_all_account_numbers,
    fetch_user_bills,
    fetch_user_bills_with_issues,
)


class BillingService:
    def get_accounts(self) -> list[str]:
        return fetch_all_account_numbers()

    def get_bills(self, account_id: str) -> list[dict]:
        bills_df = fetch_user_bills(account_id=account_id)
        return self._df_to_records(bills_df)

    def get_bill_issues(self, account_id: str, issue_type: str | None = None) -> list[dict]:
        issues_df = fetch_user_bills_with_issues(account_id=account_id, issue_type=issue_type)
        return self._df_to_records(issues_df)

    @staticmethod
    def _df_to_records(df: pd.DataFrame) -> list[dict]:
        if df is None or df.empty:
            return []
        cleaned_df = df.where(pd.notna(df), None)
        return cleaned_df.to_dict(orient="records")
