import threading
from datetime import datetime
from uuid import uuid4

from src.database.db_utils import get_session
from src.database.models import PipelineRun


class WorkflowService:
    _jobs: dict[str, dict] = {}
    _jobs_lock = threading.Lock()

    def get_recent_runs(self, limit: int = 20) -> list[dict]:
        session = get_session()
        try:
            rows = (
                session.query(PipelineRun)
                .order_by(PipelineRun.created_at.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "id": row.id,
                    "dag_id": row.dag_id,
                    "start_time": row.start_time,
                    "end_time": row.end_time,
                    "status": row.status,
                    "total_runtime": row.total_runtime,
                    "error_msg": row.error_msg,
                    "created_at": row.created_at,
                }
                for row in rows
            ]
        finally:
            session.close()

    def submit_job(self, job_type: str = "full_workflow") -> dict:
        job_id = str(uuid4())
        now = datetime.utcnow()

        with self._jobs_lock:
            self._jobs[job_id] = {
                "job_id": job_id,
                "job_type": job_type,
                "status": "queued",
                "submitted_at": now,
                "started_at": None,
                "finished_at": None,
                "result": None,
                "error": None,
            }

        thread = threading.Thread(target=self._run_job, args=(job_id,), daemon=True)
        thread.start()
        return self._jobs[job_id]

    def get_job_status(self, job_id: str) -> dict | None:
        with self._jobs_lock:
            return self._jobs.get(job_id)

    def _run_job(self, job_id: str) -> None:
        with self._jobs_lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job["status"] = "running"
            job["started_at"] = datetime.utcnow()

        try:
            from src.orchestrator import workflow_manager

            success = workflow_manager.run_full_workflow()
            with self._jobs_lock:
                job = self._jobs.get(job_id)
                if job is None:
                    return
                job["status"] = "completed" if success else "failed"
                job["result"] = bool(success)
                job["finished_at"] = datetime.utcnow()
                if not success and job["error"] is None:
                    job["error"] = "Workflow execution failed"
        except Exception as exc:
            with self._jobs_lock:
                job = self._jobs.get(job_id)
                if job is None:
                    return
                job["status"] = "failed"
                job["result"] = False
                job["error"] = str(exc)
                job["finished_at"] = datetime.utcnow()
