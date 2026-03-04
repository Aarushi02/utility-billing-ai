from fastapi import APIRouter, HTTPException

from src.api.schemas.airflow import AirflowRunStatusResponse, AirflowTriggerResponse
from src.services.airflow_service import AirflowService


router = APIRouter(prefix="/airflow")
service = AirflowService()


@router.post("/dag-runs", response_model=AirflowTriggerResponse)
def trigger_airflow_dag_run() -> AirflowTriggerResponse:
    try:
        dag_run_id = service.trigger_dag_run()
        return AirflowTriggerResponse(dag_run_id=dag_run_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/dag-runs/{dag_run_id}", response_model=AirflowRunStatusResponse)
def get_airflow_dag_run_status(dag_run_id: str) -> AirflowRunStatusResponse:
    try:
        status = service.get_run_status(dag_run_id)
        return AirflowRunStatusResponse(**status)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
