import os
from src.services.usage_tracker import get_summary


class MetricsService:
    def __init__(self):
        self.openai_model = os.getenv("OPENAI_MODEL", "")

    def get_aws_metrics(self):
        data = get_summary().get("aws", {})
        return {
            "requests": int(data.get("requests", 0)),
            "success": int(data.get("success", 0)),
            "failures": int(data.get("failures", 0)),
            "status": "ok",
            "by_operation": data.get("by_operation", {}),
            "recent_calls": data.get("recent_calls", []),
        }

    def get_openai_metrics(self):
        data = get_summary().get("llm", {})
        return {
            "month_to_date_spend": round(float(data.get("cost", 0.0)), 4),
            "requests": int(data.get("requests", 0)),
            "input_tokens": int(data.get("input_tokens", 0)),
            "output_tokens": int(data.get("output_tokens", 0)),
            "total_tokens": int(data.get("total_tokens", 0)),
            "status": "ok",
            "model": self.openai_model,
            "by_model": data.get("by_model", {}),
            "recent_calls": data.get("recent_calls", []),
        }