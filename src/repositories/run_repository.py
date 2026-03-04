from src.database.db_utils import get_session
from src.database.models import PipelineRun


class RunRepository:
    def list_recent_runs(self, limit: int = 20) -> list[dict]:
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
