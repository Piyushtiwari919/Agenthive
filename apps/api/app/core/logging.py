import hashlib
import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class StructuredJsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for attr in (
            "request_id",
            "route",
            "operation",
            "duration_ms",
            "tenant_hash",
            "outcome",
            "error_category",
        ):
            val = getattr(record, attr, None)
            if val is not None:
                payload[attr] = val
        if record.exc_info:
            payload["error_category"] = (
                record.exc_info[0].__name__ if record.exc_info[0] else "Exception"
            )
        return json.dumps(payload)


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredJsonFormatter())
    root.handlers = [handler]


def hash_tenant_for_log(tenant_id: Optional[str]) -> str:
    if not tenant_id:
        return "none"
    return hashlib.sha256(tenant_id.encode("utf-8")).hexdigest()[:10]
