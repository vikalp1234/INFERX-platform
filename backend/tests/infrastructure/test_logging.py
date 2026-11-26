import json
import logging

from app.infrastructure.observability.logging import configure_logging


def test_logging_emits_json_with_allowlisted_fields_only(capsys):
    configure_logging("INFO")
    logging.getLogger("t").info(
        "generation_completed",
        extra={"prompt_tokens": 3, "output_tokens": 5, "prompt": "LEAK-ME", "text": "LEAK-ME"},
    )
    line = capsys.readouterr().out.strip().splitlines()[-1]
    data = json.loads(line)
    assert data["message"] == "generation_completed"
    assert data["prompt_tokens"] == 3
    assert data["output_tokens"] == 5
    assert {"timestamp", "level", "logger"} <= data.keys()
    assert "prompt" not in data
    assert "text" not in data
    assert "LEAK-ME" not in line


def test_configure_logging_is_idempotent():
    configure_logging("INFO")
    configure_logging("DEBUG")
    handlers = [h for h in logging.getLogger().handlers if getattr(h, "_inferx", False)]
    assert len(handlers) == 1
