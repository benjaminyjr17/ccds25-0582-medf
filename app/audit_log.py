from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_AUDIT_DIR = Path("data") / "audit_logs"
_AUDIT_FILE = _AUDIT_DIR / "audit.jsonl"


def _to_json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _to_json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_json_safe(item) for item in value]
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()

    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        try:
            return _to_json_safe(model_dump(mode="json"))
        except Exception:
            pass

    dict_value = getattr(value, "__dict__", None)
    if isinstance(dict_value, dict):
        try:
            return _to_json_safe(dict_value)
        except Exception:
            pass

    return str(value)


def _resolve_app_version(default: str = "unknown") -> str:
    try:
        from app.main import app

        version = getattr(app, "version", default)
        return str(version) if version is not None else default
    except Exception:
        return default


def write_audit_record(
    *,
    run_id: str,
    endpoint_path: str,
    method: str,
    request_body: Any,
    response_body: Any,
    status_code: int,
    app_version: str | None = None,
) -> None:
    try:
        _AUDIT_DIR.mkdir(parents=True, exist_ok=True)

        record = {
            "run_id": str(run_id),
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "endpoint_path": str(endpoint_path),
            "method": str(method).upper(),
            "request_body": _to_json_safe(request_body),
            "response_body": _to_json_safe(response_body),
            "status_code": int(status_code),
            "app_version": str(app_version) if app_version else _resolve_app_version(),
        }

        with _AUDIT_FILE.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=True, default=str) + "\n")
    except Exception:
        # Audit logging must never break API responses.
        return
