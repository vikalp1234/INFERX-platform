import json
import logging
import sys
from datetime import UTC, datetime

# Only these extra fields may appear in logs. Prompts and generated text are never allowed.
ALLOWED_EXTRA = ("model_id", "revision", "prompt_tokens", "output_tokens", "error_type")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in ALLOWED_EXTRA:
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return json.dumps(payload)


def configure_logging(level: str) -> None:
    root = logging.getLogger()
    for handler in list(root.handlers):
        if getattr(handler, "_inferx", False):
            root.removeHandler(handler)
    handler = logging.StreamHandler(sys.stdout)
    handler._inferx = True  # type: ignore[attr-defined]
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    root.setLevel(level.upper())
