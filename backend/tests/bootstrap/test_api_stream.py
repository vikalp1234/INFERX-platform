import logging

from tests.bootstrap.test_api_endpoints import MARKER, assert_error, make_client
from tests.fakes.fake_model_execution import FakeModelExecution
from tests.sse_helpers import parse_sse


def stream(client, **body):
    body.setdefault("prompt", "hello")
    body.setdefault("max_new_tokens", 3)
    return client.post("/v1/generate/stream", json=body)


def test_stream_token_events_then_single_done():
    client, _, _ = make_client()
    response = stream(client)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["cache-control"] == "no-cache"
    events = parse_sse(response.text)
    names = [name for name, _ in events]
    assert names == ["token", "token", "token", "done"]
    assert [data["index"] for name, data in events if name == "token"] == [0, 1, 2]
    done = events[-1][1]
    assert done["request_id"] == response.headers["x-request-id"]
    assert done["finish_reason"] == "length"
    assert done["output_tokens"] == 3
    assert done["metrics"]["ttft_ms"]["provenance"] == "measured"
    assert "".join(d["text"] for n, d in events if n == "token") == "fake output text"


def test_stream_error_after_tokens_has_single_error_terminal_and_no_done():
    client, _, container = make_client(FakeModelExecution(fail_after=2))
    response = stream(client)
    events = parse_sse(response.text)
    assert [name for name, _ in events] == ["token", "token", "error"]
    error = events[-1][1]["error"]
    assert error["code"] == "inference_failed"
    assert error["request_id"] == response.headers["x-request-id"]
    assert container.gate.running == 0


def test_stream_unloaded_returns_409_not_sse():
    client, _, _ = make_client(loaded=False)
    response = stream(client)
    assert_error(response, 409, "model_not_loaded")
    assert response.headers["content-type"].startswith("application/json")


def test_stream_validation_error_is_json_422():
    client, _, _ = make_client()
    assert_error(stream(client, max_new_tokens=9999), 422, "invalid_request")
    assert_error(stream(client, prompt="  "), 422, "invalid_request")
    assert_error(
        client.post("/v1/generate/stream", json={"prompt": "x", "bogus": 1}), 422, "invalid_request"
    )


def test_stream_overloaded_before_start_is_429():
    client, _, container = make_client(max_concurrent_requests=1, max_waiting_requests=0)
    slot = container.gate.acquire()
    response = stream(client)
    assert_error(response, 429, "overloaded")
    assert response.headers["retry-after"] == "1"
    slot.release()
    assert stream(client).status_code == 200


def test_stream_releases_slot_after_completion():
    client, _, container = make_client()
    stream(client)
    assert container.gate.running == 0


def test_stream_text_with_newlines_and_unicode_roundtrips_as_single_line_events():
    class Spicy(FakeModelExecution):
        def _pieces(self, config):
            return ["line1\nline2", "   \r\n", " héllo \U0001f30d"]

    client, _, _ = make_client(Spicy())
    response = stream(client)
    events = parse_sse(response.text)
    text = "".join(d["text"] for n, d in events if n == "token")
    assert text == "line1\nline2   \r\n héllo \U0001f30d"


def test_stream_logs_contain_no_text(caplog):
    client, _, _ = make_client()
    with caplog.at_level(logging.DEBUG):
        stream(client, prompt=MARKER)
    assert MARKER not in caplog.text
    assert "fake" not in caplog.text


def test_stream_that_ends_without_finish_still_gets_one_error_terminal():
    class NoFinish(FakeModelExecution):
        def stream_generate(self, prompt, config, cancel=None):
            from app.domain.inference.streaming import TokenDelta

            yield TokenDelta(0, "partial")

    client, _, container = make_client(NoFinish())
    events = parse_sse(stream(client).text)
    assert [name for name, _ in events] == ["token", "error"]
    assert events[-1][1]["error"]["code"] == "internal_error"
    assert container.gate.running == 0
