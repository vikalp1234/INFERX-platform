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


def test_timing_fields_are_allowlisted():
    import io
    import json
    import logging

    from app.infrastructure.observability.logging import configure_logging

    stream = io.StringIO()
    configure_logging("INFO", stream)
    logging.getLogger("t").info(
        "m",
        extra={
            "ttft_ms": 1.5,
            "tpot_ms": 2.0,
            "decode_tps": 3.0,
            "total_ms": 4.0,
            "prompt": "SECRET",
        },
    )
    payload = json.loads(stream.getvalue().splitlines()[-1])
    assert payload["ttft_ms"] == 1.5 and payload["total_ms"] == 4.0
    assert "prompt" not in payload


def test_request_id_and_finish_reason_allowlisted():
    import io
    import json
    import logging

    from app.infrastructure.observability.logging import configure_logging

    stream = io.StringIO()
    configure_logging("INFO", stream)
    logging.getLogger("t").info("m", extra={"request_id": "abc", "finish_reason": "stop"})
    payload = json.loads(stream.getvalue().splitlines()[-1])
    assert payload["request_id"] == "abc"
    assert payload["finish_reason"] == "stop"
