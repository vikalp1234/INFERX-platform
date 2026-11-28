"""Server-Sent Events formatting."""

import json
from typing import Any


def format_sse(event: str, data: dict[str, Any]) -> bytes:
    """One event. JSON escapes newlines, so ``data`` is always a single line."""
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return f"event: {event}\ndata: {payload}\n\n".encode()
