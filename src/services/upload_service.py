from src.database.db_utils import fetch_all_raw_bill_docs, insert_raw_bill_document


class UploadService:
    def create_raw_document(self, metadata: dict) -> int | None:
        return insert_raw_bill_document(metadata)

    def list_raw_documents(self) -> list:
        return fetch_all_raw_bill_docs()
