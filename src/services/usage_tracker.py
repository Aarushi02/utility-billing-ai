import json
from datetime import datetime
from pathlib import Path
from threading import Lock

TRACKER_PATH = Path("data/usage_tracker.json")
_LOCK = Lock()


def _current_month() -> str:
    return datetime.utcnow().strftime("%Y-%m")


def _default_tracker() -> dict:
    return {
        "month": _current_month(),
        "llm": {
            "requests": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "cost": 0.0,
            "by_model": {},
            "recent_calls": [],
        },
        "aws": {
            "requests": 0,
            "success": 0,
            "failures": 0,
            "by_operation": {},
            "recent_calls": [],
        },
    }


def _ensure_file() -> None:
    TRACKER_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not TRACKER_PATH.exists():
        TRACKER_PATH.write_text(json.dumps(_default_tracker(), indent=2), encoding="utf-8")


def _load() -> dict:
    _ensure_file()
    data = json.loads(TRACKER_PATH.read_text(encoding="utf-8"))
    if data.get("month") != _current_month():
        data = _default_tracker()
        _save(data)
    return data


def _save(data: dict) -> None:
    TRACKER_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _estimate_llm_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    pricing = {
        "gpt-4.1-mini": {"input_per_1m": 0.40, "output_per_1m": 1.60},
        "gpt-4.1": {"input_per_1m": 2.00, "output_per_1m": 8.00},
    }
    rates = pricing.get(model)
    if not rates:
        return 0.0
    input_cost = (input_tokens / 1_000_000) * rates["input_per_1m"]
    output_cost = (output_tokens / 1_000_000) * rates["output_per_1m"]
    return round(input_cost + output_cost, 8)


def log_llm(model: str, input_tokens: int, output_tokens: int, success: bool = True) -> None:
    with _LOCK:
        data = _load()
        total_tokens = int(input_tokens) + int(output_tokens)
        cost = _estimate_llm_cost(model, int(input_tokens), int(output_tokens))

        llm = data["llm"]
        llm["requests"] += 1
        llm["input_tokens"] += int(input_tokens)
        llm["output_tokens"] += int(output_tokens)
        llm["total_tokens"] += total_tokens
        llm["cost"] = round(llm["cost"] + cost, 8)

        model_data = llm["by_model"].setdefault(
            model,
            {
                "requests": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "cost": 0.0,
            },
        )
        model_data["requests"] += 1
        model_data["input_tokens"] += int(input_tokens)
        model_data["output_tokens"] += int(output_tokens)
        model_data["total_tokens"] += total_tokens
        model_data["cost"] = round(model_data["cost"] + cost, 8)

        llm["recent_calls"].insert(
            0,
            {
                "timestamp": datetime.utcnow().isoformat(),
                "model": model,
                "input_tokens": int(input_tokens),
                "output_tokens": int(output_tokens),
                "total_tokens": total_tokens,
                "cost": cost,
                "success": success,
            },
        )
        llm["recent_calls"] = llm["recent_calls"][:20]

        _save(data)


def log_aws(operation: str, success: bool = True, error: str | None = None) -> None:
    with _LOCK:
        data = _load()
        aws = data["aws"]

        aws["requests"] += 1
        if success:
            aws["success"] += 1
        else:
            aws["failures"] += 1

        op = aws["by_operation"].setdefault(
            operation,
            {"requests": 0, "success": 0, "failures": 0},
        )
        op["requests"] += 1
        if success:
            op["success"] += 1
        else:
            op["failures"] += 1

        aws["recent_calls"].insert(
            0,
            {
                "timestamp": datetime.utcnow().isoformat(),
                "operation": operation,
                "success": success,
                "error": error,
            },
        )
        aws["recent_calls"] = aws["recent_calls"][:20]

        _save(data)


def get_summary() -> dict:
    with _LOCK:
        return _load()