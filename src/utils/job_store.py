"""
job_store.py
------------
In-memory store for tracking tariff pipeline job state.
Supports the last-write-wins pattern — registering a new job
for a doc_key automatically cancels any existing job for that key.
"""
import time
import uuid
import threading

# { doc_key: (job_id, cancel_event) }
_active_jobs: dict = {}
_job_statuses: dict = {}


def register_job(doc_key: str) -> tuple[threading.Event, str]:
    """
    Cancel any existing job for doc_key, register a new one.
    Returns (cancel_event, job_id) for the new job.
    """
    cancel_event = threading.Event()
    job_id = str(uuid.uuid4())[:8]

    if doc_key in _active_jobs:
        old_job_id, old_cancel_event = _active_jobs[doc_key]
        old_cancel_event.set()
        if old_job_id in _job_statuses:
            _job_statuses[old_job_id]["status"] = "cancelled"
        print(f"⚠️  Cancelled job {old_job_id} — superseded by {job_id}")

    _active_jobs[doc_key] = (job_id, cancel_event)
    _job_statuses[job_id] = {
        "job_id": job_id,
        "step": 0,
        "total_steps": 3,
        "message": "Starting...",
        "status": "running",
        "updated_at": time.time(),
    }
    return cancel_event, job_id


def update_job_status(job_id: str, step: int, message: str, total_steps: int = 3):
    """Update step progress and message for a running job."""
    if job_id in _job_statuses:
        _job_statuses[job_id].update({
            "step": step,
            "message": message,
            "total_steps": total_steps,
            "updated_at": time.time(),
        })


def complete_job(job_id: str):
    """Mark a job as successfully completed."""
    if job_id in _job_statuses:
        _job_statuses[job_id]["status"] = "completed"


def fail_job(job_id: str, error: str):
    """Mark a job as failed with an error message."""
    if job_id in _job_statuses:
        _job_statuses[job_id].update({
            "status": "failed",
            "message": error,
            "updated_at": time.time(),
        })


def get_job_status(job_id: str) -> dict | None:
    """Return the current status dict for a job, or None if not found."""
    return _job_statuses.get(job_id)


def cleanup_job(doc_key: str, job_id: str):
    """Remove from active jobs only if this job is still the active one."""
    if _active_jobs.get(doc_key, (None,))[0] == job_id:
        del _active_jobs[doc_key]