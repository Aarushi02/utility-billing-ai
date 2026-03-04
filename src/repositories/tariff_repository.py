from src.database.utils.tariff_and_versions_utils import (
    get_distinct_sc_codes,
    get_logic_for_sc_version,
    get_versions_for_sc,
)


class TariffRepository:
    def list_sc_codes(self) -> list[str]:
        return get_distinct_sc_codes()

    def list_versions_for_sc(self, sc_code: str) -> list[str]:
        return get_versions_for_sc(sc_code)

    def get_logic_for_version(self, sc_code: str, effective_date: str):
        return get_logic_for_sc_version(sc_code, effective_date)
