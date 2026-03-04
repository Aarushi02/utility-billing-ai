from typing import Any

from pydantic import BaseModel


class TariffScCodesResponse(BaseModel):
    sc_codes: list[str]


class TariffVersionsResponse(BaseModel):
    sc_code: str
    versions: list[str]


class TariffLogicResponse(BaseModel):
    sc_code: str
    effective_date: str
    logic: dict[str, Any]
