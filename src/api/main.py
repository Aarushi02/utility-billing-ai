from fastapi import FastAPI

from src.api.routers import airflow, bills, health, jobs, reports, runs, tariffs
from src.database.init_db import init_db


app = FastAPI(
    title="Utility Billing AI API",
    version="1.0.0",
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(airflow.router, prefix="/api/v1", tags=["airflow"])
app.include_router(tariffs.router, prefix="/api/v1", tags=["tariffs"])
app.include_router(bills.router, prefix="/api/v1", tags=["bills"])
app.include_router(runs.router, prefix="/api/v1", tags=["runs"])
app.include_router(reports.router, prefix="/api/v1", tags=["reports"])
app.include_router(jobs.router, prefix="/api/v1", tags=["jobs"])
