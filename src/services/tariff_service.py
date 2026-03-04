from src.repositories.tariff_repository import TariffRepository


class TariffService:
    def __init__(self, repository: TariffRepository | None = None) -> None:
        self.repository = repository or TariffRepository()

    def get_sc_codes(self) -> list[str]:
        return self.repository.list_sc_codes()

    def get_versions_for_sc(self, sc_code: str) -> list[str]:
        return self.repository.list_versions_for_sc(sc_code)

    def get_logic_for_sc_version(self, sc_code: str, effective_date: str):
        return self.repository.get_logic_for_version(sc_code, effective_date)
