from fastapi import APIRouter, HTTPException

from src.api.schemas.tariffs import (
    TariffLogicResponse,
    TariffScCodesResponse,
    TariffVersionsResponse,
)
from src.services.tariff_service import TariffService


router = APIRouter(prefix="/tariffs")
service = TariffService()


@router.get("/sc-codes", response_model=TariffScCodesResponse)
def get_sc_codes() -> TariffScCodesResponse:
    return TariffScCodesResponse(sc_codes=service.get_sc_codes())


@router.get("/{sc_code}/versions", response_model=TariffVersionsResponse)
def get_versions(sc_code: str) -> TariffVersionsResponse:
    versions = service.get_versions_for_sc(sc_code)
    if not versions:
        raise HTTPException(status_code=404, detail=f"No versions found for sc_code={sc_code}")
    return TariffVersionsResponse(sc_code=sc_code, versions=versions)


@router.get("/{sc_code}/versions/{effective_date}", response_model=TariffLogicResponse)
def get_logic(sc_code: str, effective_date: str) -> TariffLogicResponse:
    logic = service.get_logic_for_sc_version(sc_code, effective_date)
    if logic is None:
        raise HTTPException(
            status_code=404,
            detail=f"No logic found for sc_code={sc_code}, effective_date={effective_date}",
        )
    return TariffLogicResponse(
        sc_code=sc_code,
        effective_date=effective_date,
        logic=logic,
    )
